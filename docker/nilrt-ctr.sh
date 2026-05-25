#!/bin/bash
# nilrt-ctr.sh — Management CLI for NILRT containers.
#
# Provides discovery, configuration, software management, and monitoring
# for NILRT containers managed by docker-compose.yml.
#
# Usage:
#   bash docker/nilrt-ctr.sh <command> [arguments...]
#
# Commands:
#   status|info <target>                       Show target summary
#   set-feed|feed <target|all> <YYYYQN>        Set package feed
#   install <target> [--feed YYYYQN] <pkg...>  Install packages on a target
#   remove|uninstall <target> <pkg...>         Remove packages from a target
#   change-hostname <target> <hostname>        Set target hostname
#   shell|ssh <target>                         Open an interactive shell on a target
#   scale <service> <n>                        Scale a service to n instances
#
# Targets can be specified by container name, container ID (prefix), or
# index from managed container list (e.g. "1", "2").
#
# Examples:
#   bash docker/nilrt-ctr.sh status nilrt-slim-1
#   bash docker/nilrt-ctr.sh set-feed all 2026Q2
#   bash docker/nilrt-ctr.sh install nilrt-1 --feed 2026Q2 ni-labview-realtime
#   bash docker/nilrt-ctr.sh change-hostname nilrt-1 cRIO-test

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
DOCKER_CMD="docker"
LABEL_FILTER="label=nilrt.managed=true"

# Auto-detect NILRT image version from local docker images (used by 'scale').
if [[ -z "${NILRT_VERSION:-}" ]]; then
    NILRT_VERSION=$(docker images --format '{{.Tag}}' nilrt-runmode-container 2>/dev/null \
        | grep -v '^<none>$' | sort -V | tail -n1)
    [[ -z "$NILRT_VERSION" ]] && NILRT_VERSION="latest"
fi
export NILRT_VERSION

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    cat <<'EOF'
Usage: bash docker/nilrt-ctr.sh <command> [arguments...]

  Management CLI for NILRT containers.

Commands:
  status|info <target>                       Show target summary
  set-feed|feed <target|all> <YYYYQN>        Set package feed
  install <target> [--feed YYYYQN] <pkg...>  Install packages
  remove|uninstall <target> <pkg...>         Remove packages
  change-hostname <target> <hostname>        Set target hostname
  shell|ssh <target>                         Interactive shell
  scale <service> <n>                        Scale service instances

Targets: container name, ID prefix, or managed index.

Use native docker for non-NILRT-specific operations, for example:
    docker ps -a --filter label=nilrt.managed=true
    docker logs <container>
    docker exec -it <container> /bin/bash
    docker compose -f docker/docker-compose.yml up -d --scale nilrt=3
EOF
    exit "${1:-0}"
}

err() { echo -e "${RED}ERROR:${NC} $*" >&2; exit 1; }
warn() { echo -e "${YELLOW}WARNING:${NC} $*" >&2; }
info() { echo -e "${BLUE}==>${NC} $*"; }

# Wait for opkg lock to be released inside a container, then run opkg command.
# Retries the opkg command directly since wrapping with flock conflicts with
# opkg's internal lock acquisition (same file, different fd).
run_opkg() {
    local cid="$1"; shift
    local retries=30
    local output rc target_name
    target_name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    target_name="${target_name:-${cid:0:12}}"
    while [[ $retries -gt 0 ]]; do
        output=$($DOCKER_CMD exec "$cid" opkg "$@" 2>&1)
        rc=$?
        if [[ $rc -eq 0 ]]; then
            [[ -n "$output" ]] && echo "$output"
            return 0
        fi
        if echo "$output" | grep -q "Could not lock"; then
            info "Waiting for opkg lock on ${target_name}..."
            sleep 2
            ((retries--))
            continue
        fi
        echo "$output" >&2
        return $rc
    done
    err "Timed out waiting for opkg lock on ${target_name}"
}

# Write feed config to /etc/opkg/base-feeds.conf inside a container.
# opkg reads all *.conf in /etc/opkg/ directly, so this is the only file needed.
set_feed_on_target() {
    local cid="$1" feed="$2"
    local lv_feed="ni-lv${feed:0:4}"
    local name
    name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    name="${name:-${cid:0:12}}"
    info "Setting ${name} feed: ${feed} (LV: ${lv_feed})"
    $DOCKER_CMD exec "$cid" bash -c "
        feeds_uri=\${NILRT_FEEDS_URI:-http://nickdanger.amer.corp.natinst.com/feeds}
        ni_line=\"src/gz ni-software \${feeds_uri}/${feed}/ni-main\"
        lv_line=\"src/gz ${lv_feed} \${feeds_uri}/${feed}/${lv_feed}\"
        sed -i '/^src\/gz ni-software /d' /etc/opkg/base-feeds.conf 2>/dev/null || true
        sed -i '/^src\/gz ni-lv[0-9]/d' /etc/opkg/base-feeds.conf 2>/dev/null || true
        echo \"\${ni_line}\" >> /etc/opkg/base-feeds.conf
        echo \"\${lv_line}\" >> /etc/opkg/base-feeds.conf
    "
}

# Resolve a target argument to a container ID.
# Accepts: container name, ID prefix, or numeric index from managed list.
resolve_target() {
    local target="$1"

    # If numeric, treat as index from container list
    if [[ "$target" =~ ^[0-9]+$ ]]; then
        local containers
        mapfile -t containers < <($DOCKER_CMD ps -a --filter "$LABEL_FILTER" --format '{{.ID}}' 2>/dev/null)
        local idx=$((target - 1))
        if [[ $idx -lt 0 || $idx -ge ${#containers[@]} ]]; then
            err "Index ${target} out of range. Use 'docker ps -a --filter label=nilrt.managed=true' to see targets."
        fi
        echo "${containers[$idx]}"
        return
    fi

    # Try exact name match
    local id
    id=$($DOCKER_CMD ps -a --filter "$LABEL_FILTER" --filter "name=^${target}$" --format '{{.ID}}' 2>/dev/null | head -1)
    if [[ -n "$id" ]]; then
        echo "$id"
        return
    fi

    # Try name substring match
    id=$($DOCKER_CMD ps -a --filter "$LABEL_FILTER" --filter "name=${target}" --format '{{.ID}}' 2>/dev/null | head -1)
    if [[ -n "$id" ]]; then
        echo "$id"
        return
    fi

    # Try ID prefix
    id=$($DOCKER_CMD ps -a --filter "$LABEL_FILTER" --format '{{.ID}}' 2>/dev/null | grep "^${target}" | head -1)
    if [[ -n "$id" ]]; then
        echo "$id"
        return
    fi

    err "Target '${target}' not found. Use 'docker ps -a --filter label=nilrt.managed=true' to list targets."
}

# ---- Commands ----

cmd_show_status() {
    [[ $# -lt 1 ]] && err "Usage: nilrt-ctr.sh status <target>"
    local cid
    cid=$(resolve_target "$1")
    local name
    name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    name="${name:-${cid:0:12}}"

    local image state started ip hostname
    image=$($DOCKER_CMD inspect --format '{{.Config.Image}}' "$cid")
    state=$($DOCKER_CMD inspect --format '{{.State.Status}}' "$cid")
    started=$($DOCKER_CMD inspect --format '{{.State.StartedAt}}' "$cid")
    ip=$($DOCKER_CMD inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$cid")
    hostname=$($DOCKER_CMD exec "$cid" hostname 2>/dev/null || echo "N/A")

    echo "Name:     ${name}"
    echo "ID:       ${cid:0:12}"
    echo "Image:    ${image}"
    echo "State:    ${state}"
    echo "Started:  ${started}"
    echo "Hostname: ${hostname}"
    echo "IP:       ${ip:-N/A}"
}

cmd_set_feed() {
    [[ $# -lt 2 ]] && err "Usage: nilrt-ctr.sh set-feed <target|all> <YYYYQN>"
    local target="$1" feed="$2"

    if [[ ! "$feed" =~ ^[0-9]{4}Q[1-4]$ ]]; then
        err "Feed must be in YYYYQN format (e.g. 2026Q2)"
    fi

    local targets=()
    if [[ "$target" == "all" ]]; then
        mapfile -t targets < <($DOCKER_CMD ps -a --filter "$LABEL_FILTER" --format '{{.ID}}' 2>/dev/null)
        [[ ${#targets[@]} -eq 0 ]] && err "No managed containers found."
    else
        targets+=("$(resolve_target "$target")")
    fi

    for cid in "${targets[@]}"; do
        local state
        state=$($DOCKER_CMD inspect --format '{{.State.Status}}' "$cid")
        if [[ "$state" != "running" ]]; then
            local target_name
            target_name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
            target_name="${target_name:-${cid:0:12}}"
            warn "Skipping ${target_name} (not running)"
            continue
        fi
        set_feed_on_target "$cid" "$feed"
    done
}

cmd_install() {
    [[ $# -lt 2 ]] && err "Usage: nilrt-ctr.sh install <target> [--feed YYYYQN] <package> [package...]"
    local target="$1"; shift
    local cid
    cid=$(resolve_target "$target")
    local name
    name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    name="${name:-${cid:0:12}}"
    local feed=""

    # Parse optional --feed flag
    if [[ "${1:-}" == "--feed" ]]; then
        shift
        [[ $# -lt 1 ]] && err "--feed requires a value (e.g. 2026Q2)"
        feed="$1"; shift
        [[ $# -lt 1 ]] && err "No packages specified after --feed ${feed}"
    fi

    if [[ -n "$feed" ]]; then
        set_feed_on_target "$cid" "$feed"
    fi

    info "Installing on ${name}: $*"
    run_opkg "$cid" update
    run_opkg "$cid" install "$@"
    info "Installation complete."
}

cmd_remove() {
    [[ $# -lt 2 ]] && err "Usage: nilrt-ctr.sh remove <target> <package> [package...]"
    local target="$1"; shift
    local cid
    cid=$(resolve_target "$target")
    local name
    name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    name="${name:-${cid:0:12}}"

    info "Removing from ${name}: $*"
    run_opkg "$cid" remove "$@"
    info "Removal complete."
}

cmd_change_hostname() {
    [[ $# -lt 2 ]] && err "Usage: nilrt-ctr.sh change-hostname <target> <hostname>"
    local cid new_hostname="$2"
    cid=$(resolve_target "$1")
    local name
    name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    name="${name:-${cid:0:12}}"

    info "Setting hostname of ${name} to '${new_hostname}'..."
    $DOCKER_CMD exec "$cid" bash -c "
        echo '${new_hostname}' > /etc/hostname
        hostname '${new_hostname}'
        if command -v nirtcfg &>/dev/null; then
            nirtcfg --set section=SystemSettings,token=Host_Name,value='${new_hostname}' 2>/dev/null || true
        fi
    "
    info "Hostname set to '${new_hostname}'."
}

cmd_open_shell() {
    [[ $# -lt 1 ]] && err "Usage: nilrt-ctr.sh shell <target>"
    local cid
    cid=$(resolve_target "$1")
    local name
    name=$($DOCKER_CMD inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||')
    name="${name:-${cid:0:12}}"

    info "Opening shell on ${name}..."
    $DOCKER_CMD exec -it "$cid" /bin/bash
}

cmd_scale() {
    [[ $# -lt 2 ]] && err "Usage: nilrt-ctr.sh scale <service> <count>"
    local service="$1" count="$2"

    if ! [[ "$count" =~ ^[0-9]+$ ]]; then
        err "Count must be a positive integer."
    fi

    info "Scaling ${service} to ${count} instance(s)..."
    $DOCKER_CMD compose -f "$COMPOSE_FILE" up -d --scale "${service}=${count}" "$service"
    info "${service} scaled to ${count}."
}

# ---- Main ----

[[ $# -eq 0 ]] && usage

case "$1" in
    status|info)                shift; cmd_show_status "$@" ;;
    set-feed|feed)              shift; cmd_set_feed "$@" ;;
    install)                    shift; cmd_install "$@" ;;
    remove|uninstall)           shift; cmd_remove "$@" ;;
    change-hostname|hostname)   shift; cmd_change_hostname "$@" ;;
    shell|ssh)                  shift; cmd_open_shell "$@" ;;
    scale)                      shift; cmd_scale "$@" ;;
    -h|--help|help)       usage 0 ;;
    *)                    err "Unknown command: $1. Run 'nilrt-ctr.sh --help' for usage." ;;
esac
