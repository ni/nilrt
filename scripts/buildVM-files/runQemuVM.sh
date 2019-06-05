#!/bin/bash
set -e
SCRIPT_DIR="`dirname "$BASH_SOURCE[0]"`"
qemu-system-x86_64 \
    -enable-kvm -cpu kvm64 -smp cpus=1 \
    -m "${VM_MEM_SIZE_MB}" \
    -nographic \
    -drive if=pflash,format=raw,readonly,file="$SCRIPT_DIR/OVMF/OVMF_CODE.fd" \
    -drive if=pflash,format=raw,file="$SCRIPT_DIR/OVMF/OVMF_VARS.fd" \
    -drive file="$SCRIPT_DIR/${VM_NAME}.qcow2",index=0,media=disk
echo "DONE"
