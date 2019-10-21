#!/bin/bash
set -e

function usage() {
	cat <<EOF
$(basename "$0") [-hs] [-c cpu_count] [-m memory] [-- qemu_args [qemu_args]]

Opts:
	-h    : Display this help and exit.
	-s    : Start VM in snapshot mode (changes not saved to disk)

Args:
	cpu_count : the number of CPUs which will be available to the VM
	memory    : the amount (in MB) of memory for the VM
	qemu_args : optional arguments to append to the qemu-system-x86_64 call
EOF
}

while getopts ":c:hm:s-" opt; do
	case ${opt} in
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

SCRIPT_DIR="`dirname "$BASH_SOURCE[0]"`"
set -x
qemu-system-x86_64 \
	-enable-kvm -cpu kvm64 -smp cpus=${cpu_count:-1} \
	-m "${mem_mbs:-${VM_MEM_SIZE_MB}}" \
	-nographic \
	-drive if=pflash,format=raw,readonly,file="$SCRIPT_DIR/OVMF/OVMF_CODE.fd" \
	-drive if=pflash,format=raw,file="$SCRIPT_DIR/OVMF/OVMF_VARS.fd" \
	-drive file="$SCRIPT_DIR/${VM_NAME}.qcow2",index=0,media=disk \
	${qemu_args:-}
