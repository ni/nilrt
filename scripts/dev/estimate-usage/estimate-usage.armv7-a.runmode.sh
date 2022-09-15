#!/bin/bash

set -e

print_fs_usage() {
    local image="$1"
    # Format the UBI volume and create a clean ubifs...
    ubimkvol /dev/ubi0 -N mynandvol -m >/dev/null
    # ...reserving zero space for the root, similar to the cRIO-9068
    mkfs.ubifs -R 0 /dev/ubi0_0
    local mountpoint="$(mktemp -d)"
    mount -t ubifs ubi0 "$mountpoint"
    tar -xOf "$image" ./data.tar.gz | tar -xz -C "$mountpoint"
    sync
    echo -ne "$image\tARMv7-A\trunmode\tdisk footprint\t"
    df -h "$mountpoint" | tail -1 | awk '{ print $3; }'
    umount "$mountpoint"
    rmdir "$mountpoint"
    ubirmvol /dev/ubi0 -N mynandvol
}

# Simulate a Micron MT29F8G08ADBDA NAND flash with four partitions
# like the cRIO-9068 configuration, with the last rootfs partition
# around 942 MB.
modprobe nandsim \
    first_id_byte=0x2c  \
    second_id_byte=0xa3 \
    third_id_byte=0xd1  \
    fourth_id_byte=0x15 \
    parts=1,88,560

modprobe ubi mtd=3

modprobe ubifs

if test 0 -eq $#; then
    print_fs_usage /dev/stdin
else
    for image in "$@"; do
        print_fs_usage "$image"
    done
fi

rmmod ubifs
rmmod ubi
rmmod nandsim
