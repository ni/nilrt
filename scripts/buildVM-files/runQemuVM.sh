#!/bin/bash
set -e

# Populate the $macaddr variable with a randomly generated MAC address in the
# 52:54:::: range.
generate_random_mac() {
	printf -v macaddr "52:54:%02x:%02x:%02x:%02x" \
		$(( $RANDOM & 0xff )) $(( $RANDOM & 0xff )) \
		$(( $RANDOM & 0xff )) $(( $RANDOM & 0xff ))
}

# Print usage information to stdout.
# STDOUT: help text
usage() {
	cat <<EOF
$(basename "$0") [-h] \\
    [-a mac_address] [-b bridge] [-c cpu_count] [-m memory] [-s] \\
    [-- qemu_args [qemu_args]]

Opts:
    -h    : Display this help and exit.
    -s    : Start VM in snapshot mode (changes not saved to disk)

Args:
    -a mac_address : Use this static MAC address for the primary NIC, instead of
                     one which is randomly generated.
    -b bridge      : Add the VM as a member to this network bridge device.
    -c cpu_count   : the number of CPUs which will be available to the VM
    -m memory      : the amount (in MB) of memory for the VM
    -- qemu_args   : optional arguments to append to the qemu-system-x86_64 call
EOF
}


while getopts ":a:b:c:hm:s-" opt; do
	case ${opt} in
		a)
			macaddr=$OPTARG
			;;
		b)
			if_bridge=$OPTARG
			;;
		c)
			cpu_count=$OPTARG
			;;
		h)
			usage
			exit 0
			;;
		m)
			mem_mbs=$OPTARG
			;;
		s)
			snapshot=true
			;;
		-)
			break
			;;
		\?)
			echo "Invalid option: $OPTARG" 1>&2
			usage
			exit 2
			;;
		:)
			echo "Invalid option: $OPTARG requires an argument" 1>&2
			usage
			exit 2
			;;
	esac
done
shift $((OPTIND -1))


qemu_args=${@:-}
if [ "$snapshot" = true ] ; then
	qemu_args="-snapshot ${qemu_args}"
fi

# determine the VM's primary mac address
[ -n "${macaddr}" ] || generate_random_mac
# determine primary NIC configuration
if [ -n "${if_bridge}" ]; then
	nilrt_net0_args="tap,ifname=\"$if_bridge\",id=nilrt_net0"
else
	nilrt_net0_args="user,id=nilrt_net0"
fi

# Enable the KVM hypervisor layer, if it seems like it is supported.
if [ -w /dev/kvm ]; then
    echo "INFO: /dev/kvm detected as writable. Enabling KVM hypervisor."
    enableKVM="-enable-kvm"
else
    echo "INFO: /dev/kvm is not writable. KVM will not be enabled."
fi

SCRIPT_DIR="`dirname "$BASH_SOURCE[0]"`"
set -x
qemu-system-x86_64 \
	${enableKVM:-} -cpu qemu64 -smp cpus=${cpu_count:-1} \
	-m "${mem_mbs:-${VM_MEM_SIZE_MB}}" \
	-nographic \
	-drive if=pflash,format=raw,readonly,file="$SCRIPT_DIR/OVMF/OVMF_CODE.fd" \
	-drive if=pflash,format=raw,file="$SCRIPT_DIR/OVMF/OVMF_VARS.fd" \
	-drive file="$SCRIPT_DIR/${VM_NAME}.qcow2",index=0,media=disk \
	-device e1000,netdev=nilrt_net0,mac=$macaddr \
	-netdev ${nilrt_net0_args} \
	${qemu_args:-}
