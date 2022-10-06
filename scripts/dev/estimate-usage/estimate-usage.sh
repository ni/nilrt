#!/bin/bash

set -e

HERE="$(dirname "$(realpath "$0")")"

EXPORTS_DIR="${EXPORTS_DIR-/mnt/nirvana/perforceExports/build/exports}"

VM_DIR="${VM_DIR-/mnt/argo/RnD/RTOS/qemu_vms}"
VM_DISK="$VM_DIR/${VM_ARMV7_A-debian_with_ssh_forwarding_mtd_utils.qcow2}"
USE_CACHE="${USE_CACHE-true}"
TMP_VM_DISK="$(mktemp)"

RUNIMAGE="$(mktemp)"
SAFEIMAGE="$(mktemp)"

# If desirable, user can provide extra options for the QEMU invocation, but
# it's not always the case that they have permissions to use KVM.
#QEMU_OPTIONS="-accel kvm"

VERBOSE="${VERBOSE-true}"
log() {
    $VERBOSE && echo "$@" >&2 || true
}

cleanup() {
    rm "$TMP_VM_DISK"
    rm "$RUNIMAGE" "$SAFEIMAGE"
    kill %-
}
trap cleanup EXIT

SSH_OPTIONS="-q -o StrictHostKeyChecking=no -o UpdateHostKeys=no"

identify_latest() {
    local latest_majmin="$(ls -r "$2" | head -1)"
    local latest_export="$(ls -t "$2/$latest_majmin" | sed 'y/dabf/wxyz/' | sort -rV | sed 'y/wxyz/dabf/' | head -1)"
    log "Latest export under $2 is $latest_export"
    echo "$2/$latest_majmin/$latest_export"
}

wait_for_ssh() {
    log "Attempting SSH connection..."
    until ssh -p 2222 $SSH_OPTIONS root@localhost true; do
        sleep 1
        log "Retrying SSH connection..."
    done
}

get_latest_x86_64_images() {
    local default="$EXPORTS_DIR/ni/rtos/rtos_nilinuxrt/official/export"
    local search="${EXPORT_SEARCH_PATH_X86_64-$default}"
    local latest="$(identify_latest "$1" "$search")"
    local presuffix="targets/linuxU/x64/gcc-4.7-oe/release"
    local run_suffix="$presuffix/nilrt-base-system-image-x64.tar"
    local safe_suffix="$presuffix/standard_x64_safemode.tar.gz"
    cp -f "$latest/$run_suffix" "$1"
    cp -f "$latest/$safe_suffix" "$2"
}

get_latest_armv7_a_images() {
    local default="$EXPORTS_DIR/ni/nilr/nilrt_os_common/official/export"
    local search="${EXPORT_SEARCH_PATH_ARMV7_A-$default}"
    local latest="$(identify_latest "$1" "$search")"
    local run_presuffix="distribution-systemlink_dkms/release/RT Images/SystemLink"
    # There's a versioned directory here for some reason, but at least it's the
    # only thing there and we can just use head -1 to get it.
    run_presuffix="$run_presuffix/$(ls "$latest/$run_presuffix" | head -1)"
    local run_suffix="$run_presuffix/systemlink-linux-armv7-a.tar"
    local safe_suffix="crio_zynq_safemode.itb"
    cp -f "$latest/$run_suffix" "$1"
    cp -f "$latest/$safe_suffix" "$2"
}

if "$USE_CACHE"; then
    CACHE_DIR="${XDG_CACHE_HOME-$HOME/.cache}/nilrt-estimate-usage"
    if test ! -f "$CACHE_DIR/vm-base.qcow2"; then
        log "Retrieving disk image into cache"
        mkdir -p "$CACHE_DIR"
        cp -f "$VM_DISK" "$CACHE_DIR/vm-base.qcow2"
    fi
    log "Creating disk image backed by cached image"
    qemu-img create -q -f qcow2 -b "$CACHE_DIR/vm-base.qcow2" -F qcow2 "$TMP_VM_DISK"
else
    log "Retrieving disk image"
    cp -f "$VM_DISK" "$TMP_VM_DISK"
fi

log "Starting VM"
qemu-system-x86_64 \
    "$TMP_VM_DISK" \
    -m 512 \
    -display none \
    -netdev user,id=fwd,hostfwd=::2222-:22 -device e1000,netdev=fwd \
    $QEMU_OPTIONS &
log "VM PID is $(jobs -p %-)"
wait_for_ssh

log "Copying x86_64 scripts into VM"
scp -P 2222 $SSH_OPTIONS "$HERE/estimate-usage.x86_64.runmode.sh" root@localhost:.
scp -P 2222 $SSH_OPTIONS "$HERE/estimate-usage.x86_64.safemode.sh" root@localhost:.
get_latest_x86_64_images "$RUNIMAGE" "$SAFEIMAGE"
log "Running x86_64 subscripts in VM"
cat "$RUNIMAGE" | ssh -p 2222 $SSH_OPTIONS root@localhost ./estimate-usage.x86_64.runmode.sh | cut -d $'\t' -f 2-
cat "$SAFEIMAGE" | ssh -p 2222 $SSH_OPTIONS root@localhost ./estimate-usage.x86_64.safemode.sh | cut -d $'\t' -f 2-

log "Copying ARMv7-A scripts into VM"
scp -P 2222 $SSH_OPTIONS "$HERE/estimate-usage.armv7-a.runmode.sh" root@localhost:.
scp -P 2222 $SSH_OPTIONS "$HERE/estimate-usage.armv7-a.safemode.sh" root@localhost:.
get_latest_armv7_a_images "$RUNIMAGE" "$SAFEIMAGE"
log "Running ARMv7-A subscripts in VM"
cat "$RUNIMAGE" | ssh -p 2222 $SSH_OPTIONS root@localhost ./estimate-usage.armv7-a.runmode.sh | cut -d $'\t' -f 2-
cat "$SAFEIMAGE" | ssh -p 2222 $SSH_OPTIONS root@localhost ./estimate-usage.armv7-a.safemode.sh | cut -d $'\t' -f 2-
