#!/bin/bash

set -e

print_fs_usage() {
    local image="$1"
    local fs="$(mktemp)"
    truncate -s 2G "$fs"
    mkfs.ext4 -q "$fs"
    local mountpoint="$(mktemp -d)"
    mount -o loop "$fs" "$mountpoint"
    tar -xOf "$image" data.tar.gz | tar -xz -C "$mountpoint"
    sync
    echo -ne "$image\tx86_64\trunmode\tdisk footprint\t"
    df -h "$mountpoint" | tail -1 | awk '{ print $3; }'
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
