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
    [-a mac_address] [-b bridge] [-c cpu_count] [-m memory] [-s] [-g] \\
    [-- qemu_args [qemu_args]]

Opts:
    -h    : Display this help and exit.
    -g    : Start VM with arguments appropriate for graphical usage
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


while getopts ":a:b:c:ghm:s-" opt; do
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
		g)
			graphical=true
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
if [ "$graphical" = true ] ; then
	# provide pointer device with absolute coordinates
	qemu_args="-usb -device usb-tablet ${qemu_args}"
	# add a serial device similar to what -nographic provides
	qemu_args="-chardev stdio,id=gserial,mux=on,signal=off -serial chardev:gserial ${qemu_args}"
else
	qemu_args="-nographic ${qemu_args}"
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
	${enableKVM:-} -cpu qemu64 -smp cpus=${cpu_count:-1} -machine vmport=off \
	-m "${mem_mbs:-${VM_MEM_SIZE_MB}}" \
	-drive if=pflash,format=raw,readonly,file="$SCRIPT_DIR/OVMF/OVMF_CODE.fd" \
	-drive if=pflash,format=raw,file="$SCRIPT_DIR/OVMF/OVMF_VARS.fd" \
	-drive file="$SCRIPT_DIR/${PRIMARY_DISK}",index=0,media=disk \
	-device e1000,netdev=nilrt_net0,mac=$macaddr \
	-netdev ${nilrt_net0_args} \
	${qemu_args:-}
