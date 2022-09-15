#!/bin/bash

set -e

print_fs_usage() {
    local input_image="$1"
    local image="$input_image"
    if test ! -f "$image"; then
        # We need to look at its filesize and read it multiple times, so if it's
        # not a plain file, we should make it into one.
        image="$(mktemp)"
        cat "$input_image" >"$image"
    fi
    echo -ne "$image\tARMv7-A\tsafemode\tdisk footprint\t"
    du --apparent-size -h "$image" | awk '{ print $1; }'
    echo -ne "$image\tARMv7-A\tsafemode\tkernel + ramdisk\t"
    local kernel_size="$(dumpimage "$image" -T flat_dt -p 0 -o /dev/fd/3 3>&1 >/dev/null | gzip -d | wc -c)"
    local ramdisk_size="$(dumpimage "$image" -T flat_dt -p 16 -o /dev/fd/3 3>&1 >/dev/null | xz -d | wc -c)"
    numfmt --to=iec "$(($kernel_size + $ramdisk_size))"
    if test "$input_image" != "$image"; then
        rm "$image"
    fi
}

if test 0 -eq $#; then
    print_fs_usage /dev/stdin
else
    for image in "$@"; do
        print_fs_usage "$image"
    done
fi
