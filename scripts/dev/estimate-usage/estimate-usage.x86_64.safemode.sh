#!/bin/bash

set -e

print_fs_usage() {
    local image="$1"
    local fs="$(mktemp)"
    truncate -s 1G "$fs"
    mkfs.ext4 -q "$fs"
    local mountpoint="$(mktemp -d)"
    mount -o loop "$fs" "$mountpoint"
    tar -xzf "$image" -C "$mountpoint"
    sync
    echo -ne "$image\tx86_64\tsafemode\tdisk footprint\t"
    df -h "$mountpoint" | tail -1 | awk '{ print $3; }'
    echo -ne "$image\tx86_64\tsafemode\tkernel + ramdisk\t"
    local kernel_size="$(du -b "$mountpoint/bzImage" | awk '{ print $1; }')"
    local ramdisk_size="$(xz -d <"$mountpoint/ramdisk.xz" | wc -c)"
    numfmt --to=iec "$(($kernel_size + $ramdisk_size))"
    umount "$mountpoint"
    rmdir "$mountpoint"
    rm "$fs"
}

if test 0 -eq $#; then
    print_fs_usage /dev/stdin
else
    for image in "$@"; do
        print_fs_usage "$image"
    done
fi
