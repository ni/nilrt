#!/bin/bash
# Create a macvlan network for NILRT containers so they are accessible
# from remote hosts on the LAN.
#
# Macvlan gives each container its own IP address on the physical network,
# making it behave like a standalone machine. Remote hosts can reach the
# container directly without port forwarding.
#
# Prerequisites:
#   - Docker or podman must be installed.
#   - The host's physical network interface must be up.
#   - An IP range on the LAN must be reserved for containers (to avoid
#     DHCP conflicts). Coordinate with your network administrator.
#
# Usage:
#   ./setup-nilrt-network.sh [OPTIONS]
#
# After setup, launch containers with collision-free IPs. nilrt-ctr.sh is
# Docker/Compose-specific (it uses 'docker network inspect' and
# 'docker compose'):
#   bash docker/nilrt-ctr.sh run nilrt
#   bash docker/nilrt-ctr.sh run nilrt-slim -n 3
#
# For podman, assign a free address yourself with an explicit --ip, e.g.:
#   podman run -it --network=nilrt-net --ip 192.0.2.65 nilrt-runmode-container:11.6
#
# Examples:
#   ./setup-nilrt-network.sh
#   ./setup-nilrt-network.sh -i eth0 -s 192.0.2.0/24 -g 192.0.2.1 -r 192.0.2.64/26
#   ./setup-nilrt-network.sh --runtime podman

set -euo pipefail

# Defaults — adjust to match your LAN.
PARENT_IFACE=""
SUBNET=""
GATEWAY=""
IP_RANGE=""
NETWORK_NAME="nilrt-net"
RUNTIME="docker"
DRY_RUN=""
SHIM_IFACE="nilrt-shim"
SHIM_IP=""

usage() {
	cat >&2 <<EOF
Usage: $(basename "$0") [OPTIONS]

Create a macvlan network for NILRT containers, giving each container
its own IP on the physical LAN.

Options:
  -i, --interface IFACE    Parent network interface (default: auto-detect)
  -s, --subnet CIDR        LAN subnet in CIDR notation (default: auto-detect)
  -g, --gateway IP         LAN gateway IP (default: auto-detect)
  -r, --ip-range CIDR      IP range for containers (default: none, DHCP-like)
                           Recommended: reserve a small range to avoid conflicts,
                           e.g. 192.0.2.64/26 gives .64-.127
  -N, --name NAME          Network name (default: nilrt-net)
      --runtime RT         Container runtime: docker or podman (default: docker)
      --shim-ip IP         IP address to assign to the shim interface
                           (default: last usable IP in --ip-range, or in the
                           detected subnet if --ip-range is omitted)
  -n, --dry-run            Print commands without executing
  -h, --help               Show this help message

Examples:
  # Auto-detect interface and subnet:
  $(basename "$0")

  # Explicit configuration:
  $(basename "$0") -i eth0 -s 192.0.2.0/24 -g 192.0.2.1 -r 192.0.2.64/26

  # Use podman instead of docker:
  $(basename "$0") --runtime podman

  # Specify shim IP for host-to-container connectivity:
  $(basename "$0") -r 192.0.2.64/26
  $(basename "$0") --shim-ip 192.0.2.127 -r 192.0.2.64/26
EOF
	exit "${1:-2}"
}

log() { echo "==> $*"; }
err() { echo "ERROR: $*" >&2; exit 1; }

# Run a command, or print it if --dry-run is set.
run_cmd() {
	if [[ -n "$DRY_RUN" ]]; then
		echo "[dry-run] $*"
	else
		"$@"
	fi
}

# Print the last usable host IP in a CIDR range.
last_host_ip() {
	python3 -c "
import ipaddress, sys
net = ipaddress.ip_network(sys.argv[1], strict=False)
if net.num_addresses == 1:
    print(net.network_address)
elif net.num_addresses == 2:
    print(net.broadcast_address)
else:
    print(net.broadcast_address - 1)" "$1"
}

# Convert a host/prefix to its network address (e.g. 192.0.2.100/24 -> 192.0.2.0/24).
network_address() {
	python3 -c "
import ipaddress, sys
print(ipaddress.ip_network(sys.argv[1], strict=False))" "$1"
}

# Auto-detect the default route interface, subnet, and gateway.
auto_detect_network() {
	if [[ -z "$PARENT_IFACE" ]]; then
		PARENT_IFACE=$(ip -o route get 8.8.8.8 2>/dev/null | sed -n 's/.*dev \([^ ]*\).*/\1/p')
		if [[ -z "$PARENT_IFACE" ]]; then
			err "Could not auto-detect network interface. Use -i to specify."
		fi
		log "Auto-detected interface: ${PARENT_IFACE}"
	fi

	if [[ -z "$SUBNET" ]]; then
		SUBNET=$(ip -o -4 addr show dev "$PARENT_IFACE" scope global | awk '{print $4}' | head -1)
		if [[ -z "$SUBNET" ]]; then
			err "Could not auto-detect subnet for ${PARENT_IFACE}. Use -s to specify."
		fi
		# Convert host address to network address (e.g. 192.0.2.100/24 -> 192.0.2.0/24)
		SUBNET=$(network_address "$SUBNET") \
			|| err "Could not compute network address from ${SUBNET}. Use -s to specify."
		log "Auto-detected subnet: ${SUBNET}"
	fi

	if [[ -z "$GATEWAY" ]]; then
		GATEWAY=$(ip -o route show default dev "$PARENT_IFACE" 2>/dev/null | awk '{print $3}' | head -1)
		if [[ -z "$GATEWAY" ]]; then
			err "Could not auto-detect gateway for ${PARENT_IFACE}. Use -g to specify."
		fi
		log "Auto-detected gateway: ${GATEWAY}"
	fi
}

# --- Argument parsing ---

while [[ $# -gt 0 ]]; do
	case "$1" in
		-h|--help)        usage 0 ;;
		-i|--interface)   shift; PARENT_IFACE="${1:?--interface requires a value}"; shift ;;
		-s|--subnet)      shift; SUBNET="${1:?--subnet requires a value}"; shift ;;
		-g|--gateway)     shift; GATEWAY="${1:?--gateway requires a value}"; shift ;;
		-r|--ip-range)    shift; IP_RANGE="${1:?--ip-range requires a value}"; shift ;;
		-N|--name)        shift; NETWORK_NAME="${1:?--name requires a value}"; shift ;;
		--runtime)        shift; RUNTIME="${1:?--runtime requires a value}"; shift ;;
		--shim-ip)        shift; SHIM_IP="${1:?--shim-ip requires a value}"; shift ;;
		-n|--dry-run)     DRY_RUN=1; shift ;;
		-*)               err "Unknown option: $1" ;;
		*)                err "Unexpected argument: $1" ;;
	esac
done

# Validate runtime
case "$RUNTIME" in
	docker|podman) ;;
	*) err "Unsupported runtime: ${RUNTIME}. Use 'docker' or 'podman'." ;;
esac

if ! command -v "$RUNTIME" &>/dev/null; then
	err "${RUNTIME} is not installed or not in PATH."
fi

# Podman macvlan requires root; prepend sudo if not already root.
RUNTIME_CMD=("$RUNTIME")
if [[ "$RUNTIME" == "podman" && "${EUID:-$(id -u)}" -ne 0 ]]; then
	if ! command -v sudo &>/dev/null; then
		err "podman macvlan requires root privileges; install sudo or run as root."
	fi
	RUNTIME_CMD=(sudo "$RUNTIME")
fi

# Check if network already exists
NETWORK_EXISTS=""
if "${RUNTIME_CMD[@]}" network inspect "$NETWORK_NAME" &>/dev/null; then
	NETWORK_EXISTS=1
	log "Network '${NETWORK_NAME}' already exists."

	NETWORK_INSPECT_JSON=$("${RUNTIME_CMD[@]}" network inspect "$NETWORK_NAME")
	printf '%s\n' "$NETWORK_INSPECT_JSON" | grep -E '"Subnet"|"Gateway"|"parent"' || true

	EXISTING_PARENT_IFACE=$(printf '%s\n' "$NETWORK_INSPECT_JSON" \
		| python3 -c "import sys,json; data=json.load(sys.stdin)[0]; print(data.get('Options', {}).get('parent', ''))" 2>/dev/null)
	EXISTING_SUBNET=$(printf '%s\n' "$NETWORK_INSPECT_JSON" \
		| python3 -c "import sys,json; data=json.load(sys.stdin)[0]; ipam=data.get('IPAM', {}).get('Config', []); print(ipam[0].get('Subnet', '') if ipam else '')" 2>/dev/null)
	EXISTING_GATEWAY=$(printf '%s\n' "$NETWORK_INSPECT_JSON" \
		| python3 -c "import sys,json; data=json.load(sys.stdin)[0]; ipam=data.get('IPAM', {}).get('Config', []); print(ipam[0].get('Gateway', '') if ipam else '')" 2>/dev/null)

	if [[ -n "$PARENT_IFACE" && -n "$EXISTING_PARENT_IFACE" && "$PARENT_IFACE" != "$EXISTING_PARENT_IFACE" ]]; then
		err "Existing network '${NETWORK_NAME}' uses parent interface '${EXISTING_PARENT_IFACE}', but --interface specified '${PARENT_IFACE}'."
	fi
	if [[ -n "$SUBNET" && -n "$EXISTING_SUBNET" && "$SUBNET" != "$EXISTING_SUBNET" ]]; then
		err "Existing network '${NETWORK_NAME}' uses subnet '${EXISTING_SUBNET}', but --subnet specified '${SUBNET}'."
	fi
	if [[ -n "$GATEWAY" && -n "$EXISTING_GATEWAY" && "$GATEWAY" != "$EXISTING_GATEWAY" ]]; then
		err "Existing network '${NETWORK_NAME}' uses gateway '${EXISTING_GATEWAY}', but --gateway specified '${GATEWAY}'."
	fi

	# Reuse the existing network settings for shim setup.
	[[ -n "$EXISTING_PARENT_IFACE" ]] && PARENT_IFACE="$EXISTING_PARENT_IFACE"
	[[ -n "$EXISTING_SUBNET" ]]       && SUBNET="$EXISTING_SUBNET"
	[[ -n "$EXISTING_GATEWAY" ]]      && GATEWAY="$EXISTING_GATEWAY"
fi

auto_detect_network

# Determine shim IP: explicit > auto-compute from ip-range > auto-compute from subnet
if [[ -z "$SHIM_IP" ]]; then
	if [[ -n "$IP_RANGE" ]]; then
		SHIM_IP=$(last_host_ip "$IP_RANGE") \
			|| err "Could not compute shim IP from ${IP_RANGE}."
		log "Auto-selected shim IP: ${SHIM_IP} (last address in --ip-range)"
	else
		SHIM_IP=$(last_host_ip "$SUBNET") \
			|| err "Could not compute shim IP from ${SUBNET}."
		log "Auto-selected shim IP: ${SHIM_IP} (last address in subnet)"
	fi
fi

# Enable promiscuous mode on the parent interface so the NIC accepts frames
# destined for container MAC addresses (required in VMs like VirtualBox).
if ! ip link show "$PARENT_IFACE" | grep -q PROMISC; then
	log "Enabling promiscuous mode on ${PARENT_IFACE}"
	run_cmd sudo ip link set "$PARENT_IFACE" promisc on
else
	log "Promiscuous mode already enabled on ${PARENT_IFACE}"
fi

if [[ -z "$NETWORK_EXISTS" ]]; then
	# Build the create command
	cmd=("${RUNTIME_CMD[@]}" network create -d macvlan
		--subnet="$SUBNET"
		--gateway="$GATEWAY"
		-o parent="$PARENT_IFACE"
	)

	# Docker supports macvlan_mode option; podman uses bridge mode by default.
	if [[ "$RUNTIME" == "docker" ]]; then
		cmd+=(-o macvlan_mode=bridge)
	fi

	if [[ -n "$IP_RANGE" ]]; then
		cmd+=(--ip-range="$IP_RANGE")
	fi

	# Reserve the shim IP so the runtime's IPAM never assigns it to a container.
	# --aux-address is supported by Docker and podman >= 4.0.
	if [[ "$RUNTIME" == "podman" ]]; then
		PODMAN_VERSION=$("$RUNTIME" --version 2>/dev/null | awk '{print $NF}')
		PODMAN_MAJOR=$(printf '%s\n' "$PODMAN_VERSION" | cut -d. -f1)
		if [[ "${PODMAN_MAJOR:-0}" -lt 4 ]]; then
			log "WARNING: podman ${PODMAN_VERSION} does not support --aux-address."
			log "  The shim IP (${SHIM_IP}) is not reserved from IPAM and may conflict"
			log "  with a container IP. Please upgrade to podman >= 4.0 or use --shim-ip"
			log "  with an IP outside the container allocation range."
		else
			cmd+=(--aux-address="nilrt-shim=${SHIM_IP}")
		fi
	else
		cmd+=(--aux-address="nilrt-shim=${SHIM_IP}")
	fi

	cmd+=("$NETWORK_NAME")

	log "Creating macvlan network: ${NETWORK_NAME}"
	log "  Interface: ${PARENT_IFACE}"
	log "  Subnet:    ${SUBNET}"
	log "  Gateway:   ${GATEWAY}"
	log "  Shim IP:   ${SHIM_IP} (reserved from IPAM)"
	if [[ -n "$IP_RANGE" ]]; then
		log "  IP range:  ${IP_RANGE}"
	fi

	run_cmd "${cmd[@]}"

	log "Network '${NETWORK_NAME}' created successfully."
fi

# --- Host-to-container connectivity via macvlan shim ---
log ""
log "Setting up host-access shim interface: ${SHIM_IFACE}"

SHIM_ROUTE="${IP_RANGE:-$SUBNET}"

if ip link show "$SHIM_IFACE" &>/dev/null; then
	log "Shim interface '${SHIM_IFACE}' already exists, ensuring configuration."
else
	run_cmd sudo ip link add "$SHIM_IFACE" link "$PARENT_IFACE" type macvlan mode bridge
fi

if ! ip addr show dev "$SHIM_IFACE" | grep -q "inet ${SHIM_IP}/32"; then
	run_cmd sudo ip addr add "${SHIM_IP}/32" dev "$SHIM_IFACE"
fi

run_cmd sudo ip link set "$SHIM_IFACE" up

# Route container traffic through the shim (use ip-range if set, else full subnet)
if ! ip route show "$SHIM_ROUTE" dev "$SHIM_IFACE" | grep -q "^${SHIM_ROUTE}[[:space:]]"; then
	run_cmd sudo ip route add "$SHIM_ROUTE" dev "$SHIM_IFACE"
fi

log "Host can now reach containers on ${SHIM_ROUTE} via shim ${SHIM_IP}"

log ""
log "To remove the shim later:"
log "  sudo ip link del ${SHIM_IFACE}"

log ""
if [[ "$RUNTIME" == "podman" ]]; then
	log "Launch containers with an explicit free --ip (nilrt-ctr.sh is Docker-only):"
	log "  podman run -it --network=${NETWORK_NAME} --ip <free-ip> nilrt-runmode-container"
else
	log "Launch containers with collision-free IPs:"
	log "  bash docker/nilrt-ctr.sh run nilrt"
	log "  bash docker/nilrt-ctr.sh run nilrt-slim -n 3"
fi
