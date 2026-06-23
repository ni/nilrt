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
#   run [nilrt|nilrt-slim] [-n N]               Launch N collision-free containers
#   status|info <target>                       Show target summary
#   set-feed|feed <target|all> <YYYYQN>        Set package feed
#   install <target> [--feed YYYYQN] <pkg...>  Install packages on a target
#   remove|uninstall <target> <pkg...>         Remove packages from a target
#   change-hostname <target> <hostname>        Set target hostname
#   shell|ssh <target>                         Open an interactive shell on a target
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

# Macvlan network and LAN-scan settings used by the 'run' command to
# assign collision-free IP addresses. Overridable via environment.
NETWORK_NAME="${NILRT_NETWORK:-nilrt-net}"
SCAN="${NILRT_SCAN:-1}"
SCAN_TIMEOUT="${NILRT_SCAN_TIMEOUT:-1}"
MAX_SWEEP_HOSTS=1024
DRY_RUN=""
USED_IPS=()

# Auto-detect NILRT image version from local docker images (used by 'run').
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
  run [nilrt|nilrt-slim] [-n N]              Launch N containers with
                                             collision-free LAN IP addresses
  status|info <target>                       Show target summary
  set-feed|feed <target|all> <YYYYQN>        Set package feed
  install <target> [--feed YYYYQN] <pkg...>  Install packages
  remove|uninstall <target> <pkg...>         Remove packages
  change-hostname <target> <hostname>        Set target hostname
  shell|ssh <target>                         Interactive shell

Targets: container name, ID prefix, or managed index.

'run' scans the LAN, picks free IPs, and pins them via Compose (NILRT_IP).
Options: -n/--count N, -r/--ip-range CIDR, --no-scan, --dry-run.

Use native docker for non-NILRT-specific operations, for example:
    docker ps -a --filter label=nilrt.managed=true
    docker logs <container>
    docker exec -it <container> /bin/bash
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

# Print the next free sequential index for naming containers of a service,
# such that "${service}-${index}" does not collide with an existing managed
# container. Indexes start at 1, e.g. nilrt-1, nilrt-2, nilrt-slim-1.
next_name_index() {
    local service="$1" max=0 n nm
    local names
    mapfile -t names < <($DOCKER_CMD ps -a --filter "$LABEL_FILTER" --format '{{.Names}}' 2>/dev/null)
    for nm in "${names[@]}"; do
        if [[ "$nm" =~ ^${service}-([0-9]+)$ ]]; then
            n="${BASH_REMATCH[1]}"
            (( n > max )) && max=$n
        fi
    done
    echo $((max + 1))
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

# ---- Collision-free IP assignment ----
# Macvlan IPAM hands out the lowest free address from each host's local view,
# so independent hosts collide on .2/.3/.4... These helpers scan the LAN at
# launch time and pin a verified-free address via Compose (NILRT_IP).

# Print every host IP within a CIDR, one per line (network/broadcast excluded
# for ranges larger than a /31).
hosts_in_cidr() {
    python3 -c "
import ipaddress, sys
net = ipaddress.ip_network(sys.argv[1], strict=False)
hosts = net.hosts() if net.num_addresses > 2 else iter(net)
for ip in hosts:
    print(ip)" "$1"
}

# Print the number of addresses in a CIDR.
range_size() {
    python3 -c "
import ipaddress, sys
print(ipaddress.ip_network(sys.argv[1], strict=False).num_addresses)" "$1"
}

# Filter a newline-separated list of IPs on stdin to those within a CIDR.
filter_ips_in_cidr() {
    python3 -c "
import ipaddress, sys
net = ipaddress.ip_network(sys.argv[1], strict=False)
for line in sys.stdin:
    ip = line.strip()
    if not ip:
        continue
    try:
        if ipaddress.ip_address(ip) in net:
            print(ip)
    except ValueError:
        pass" "$1"
}

# Return success if an address answers an ICMP echo within SCAN_TIMEOUT.
ip_is_live() {
    ping -c1 -W"$SCAN_TIMEOUT" "$1" &>/dev/null
}

# Discover in-use addresses on the LAN within a CIDR: the gateway, an active
# arp-scan when available, otherwise a parallel ICMP ping sweep read back from
# the kernel ARP table. Active probing is skipped for ranges larger than
# MAX_SWEEP_HOSTS. Prints one IP per line, sorted and de-duplicated.
scan_used_ips() {
    local cidr="$1" size active=1
    size=$(range_size "$cidr")
    if [[ "${size:-0}" -gt "$MAX_SWEEP_HOSTS" ]]; then
        active=""
        echo "==> Range ${cidr} has ${size} addresses (> ${MAX_SWEEP_HOSTS}); reading the ARP table only." >&2
    fi

    {
        [[ -n "$GATEWAY" ]] && echo "$GATEWAY"

        if [[ -n "$active" ]] && command -v arp-scan &>/dev/null; then
            (sudo -n arp-scan --interface="$PARENT_IFACE" --retry=2 "$cidr" 2>/dev/null || true) \
                | awk '$1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ {print $1}'
        else
            if [[ -n "$active" ]]; then
                local ip
                while IFS= read -r ip; do
                    ping -c1 -W"$SCAN_TIMEOUT" "$ip" &>/dev/null &
                done < <(hosts_in_cidr "$cidr")
                wait || true
            fi
            ip neigh show 2>/dev/null \
                | awk 'toupper($0) !~ /FAILED|INCOMPLETE/ && $1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ {print $1}'
        fi
    } | filter_ips_in_cidr "$cidr" | sort -u -t. -k1,1n -k2,2n -k3,3n -k4,4n
}

# Populate SUBNET, GATEWAY, NET_RANGE, PARENT_IFACE and RESERVED_IPS (network
# reservations plus IPs of locally-attached containers) from the macvlan
# network's inspect output.
get_network_config() {
    local json
    json=$($DOCKER_CMD network inspect "$NETWORK_NAME" 2>/dev/null) \
        || err "Network '${NETWORK_NAME}' not found. Create it first with setup-nilrt-network.sh."

    read -r SUBNET GATEWAY NET_RANGE PARENT_IFACE <<<"$(printf '%s' "$json" | python3 -c "
import sys, json
d = json.load(sys.stdin)[0]
cfg = (d.get('IPAM', {}).get('Config') or [{}])[0]
print(cfg.get('Subnet', '') or '_', cfg.get('Gateway', '') or '_',
      cfg.get('IPRange', '') or '_', d.get('Options', {}).get('parent', '') or '_')")"
    # '_' is an empty-field placeholder so positional read() doesn't collapse
    # adjacent blanks (e.g. a missing IPRange) and shift later fields.
    [[ "$SUBNET" == "_" ]] && SUBNET=""
    [[ "$GATEWAY" == "_" ]] && GATEWAY=""
    [[ "$NET_RANGE" == "_" ]] && NET_RANGE=""
    [[ "$PARENT_IFACE" == "_" ]] && PARENT_IFACE=""
    [[ -n "$SUBNET" ]] || err "Could not determine subnet for network '${NETWORK_NAME}'."

    mapfile -t RESERVED_IPS < <(printf '%s' "$json" | python3 -c "
import sys, json
d = json.load(sys.stdin)[0]
out = set()
for v in (d.get('IPAM', {}).get('Config') or [{}])[0].get('AuxiliaryAddresses', {}).values():
    out.add(v)
for c in (d.get('Containers') or {}).values():
    addr = c.get('IPv4Address', '')
    if addr:
        out.add(addr.split('/')[0])
for ip in sorted(out):
    print(ip)")
}

# Print the host addresses in CIDR that are not in USED_IPS, in random order so
# simultaneous launches on different hosts rarely pick the same address.
free_ips_in() {
    printf '%s\n' "${USED_IPS[@]:-}" | python3 -c "
import ipaddress, random, sys
net = ipaddress.ip_network(sys.argv[1], strict=False)
used = {line.strip() for line in sys.stdin if line.strip()}
hosts = net.hosts() if net.num_addresses > 2 else iter(net)
free = [str(ip) for ip in hosts if str(ip) not in used]
random.shuffle(free)
print(*free, sep='\n')" "$1"
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

cmd_run() {
    local service="nilrt" count=1 range=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--count)     shift; count="${1:?--count requires a value}"; shift ;;
            -r|--ip-range)  shift; range="${1:?--ip-range requires a value}"; shift ;;
            --no-scan)      SCAN=""; shift ;;
            --dry-run)      DRY_RUN=1; shift ;;
            nilrt|nilrt-slim) service="$1"; shift ;;
            -*)             err "Unknown run option: $1" ;;
            *)              err "Unknown service '$1' (expected 'nilrt' or 'nilrt-slim')." ;;
        esac
    done
    [[ "$count" =~ ^[0-9]+$ && "$count" -ge 1 ]] || err "Count must be a positive integer."

    # Read the network's subnet/gateway/range and the addresses already taken
    # by reservations or locally-attached containers.
    local SUBNET GATEWAY NET_RANGE PARENT_IFACE
    local RESERVED_IPS=()
    get_network_config

    local alloc="${range:-${NET_RANGE:-$SUBNET}}"

    # Seed the in-use set, then scan the LAN for everything else that's live.
    USED_IPS=()
    [[ -n "$GATEWAY" ]] && USED_IPS+=("$GATEWAY")
    USED_IPS+=("${RESERVED_IPS[@]:-}")
    if [[ -n "$SCAN" ]]; then
        info "Scanning ${alloc} for in-use IP addresses (this may take a moment)..."
        local scanned=()
        mapfile -t scanned < <(scan_used_ips "$alloc")
        USED_IPS+=("${scanned[@]:-}")
        info "Detected ${#scanned[@]} in-use address(es) on the LAN."
    else
        warn "LAN scan disabled; only reservations and local container IPs are avoided."
    fi
    mapfile -t USED_IPS < <(printf '%s\n' "${USED_IPS[@]}" | awk 'NF' \
        | sort -u -t. -k1,1n -k2,2n -k3,3n -k4,4n)

    # Choose COUNT distinct free addresses, giving each a final liveness probe
    # to catch anything the scan missed (or a cross-host race).
    local ips=() ip
    while IFS= read -r ip; do
        [[ -z "$DRY_RUN" ]] && ip_is_live "$ip" && continue
        ips+=("$ip")
        [[ ${#ips[@]} -ge $count ]] && break
    done < <(free_ips_in "$alloc")
    [[ ${#ips[@]} -ge $count ]] \
        || err "Only ${#ips[@]} free address(es) available in ${alloc}; needed ${count}."

    # Launch one container per address. Compose's --scale cannot pin distinct
    # static IPs, so each instance is its own single-container project keyed by
    # its sequential name (nilrt-1, nilrt-2, ...). NILRT_IP is substituted into
    # ipv4_address and NILRT_NAME into container_name so the container gets a
    # predictable, collision-free name independent of its IP.
    local next
    next=$(next_name_index "$service")

    local project name
    for ip in "${ips[@]}"; do
        name="${service}-${next}"
        project="$name"
        next=$((next + 1))
        info "Launching ${name} at ${ip}"
        if [[ -n "$DRY_RUN" ]]; then
            echo "[dry-run] NILRT_IP=${ip} NILRT_NAME=${name} ${DOCKER_CMD} compose -f ${COMPOSE_FILE} -p ${project} up -d ${service}"
            continue
        fi
        NILRT_IP="$ip" NILRT_NAME="$name" $DOCKER_CMD compose -f "$COMPOSE_FILE" -p "$project" up -d "$service"
    done
    info "Launched ${#ips[@]} ${service} container(s)."
}

# ---- Main ----

[[ $# -eq 0 ]] && usage

case "$1" in
    run|up)                     shift; cmd_run "$@" ;;
    status|info)                shift; cmd_show_status "$@" ;;
    set-feed|feed)              shift; cmd_set_feed "$@" ;;
    install)                    shift; cmd_install "$@" ;;
    remove|uninstall)           shift; cmd_remove "$@" ;;
    change-hostname|hostname)   shift; cmd_change_hostname "$@" ;;
    shell|ssh)                  shift; cmd_open_shell "$@" ;;
    -h|--help|help)       usage 0 ;;
    *)                    err "Unknown command: $1. Run 'nilrt-ctr.sh --help' for usage." ;;
esac
