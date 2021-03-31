#!/bin/bash
set -euo pipefail

IMAGE_FILE="../build/tmp-glibc/deploy/images/x64/nilrt-base-bundle-image-x64.tar.bz2"
DISK_CONFIG="../sources/meta-nilrt/recipes-core/initrdscripts/files/disk_config_x64"
ASK_FIRST=true

if [ -e ${DISK_CONFIG} ] ; then
   source ${DISK_CONFIG}
else
   error_and_die "disk_config_x64 not found"
fi

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

cleanup () {
    local exitCode="$?"

    set +e

    if [ -e "${A_MOUNT:-}" ] ; then
        umount ${A_MOUNT} >/dev/null 2>&1
        rm -fr ${A_MOUNT}
    fi

    exit "$exitCode"
}

trap cleanup EXIT

print_usage () {
cat <<EOF
Usage: buildUSB.sh -h|-l|[-i boot-image-file] [-y] USB_DEVICE

Options:
  -h         Print this help message and exit
  -l         List valid removable devices and exit
  -i         specify path to boot image file
  -y         do not ask for confirmation
  USB_DEVICE use specified block device (ie /dev/sdX)
EOF
}

print_usage_and_die () {
    local rc=${1:-2}
    if [ $rc -ne 0 ]; then
        exec 1>&2
    fi
    print_usage
    exit $rc
}

# Checks a device to make sure it meets the requirements for USB provisioning
# $1 - path to /sys/block/<dev> to check
#
# 1) device must have a non-zero capacity
# 2) device must not be read-only
# 3) device must be a removable device
# 4) device should not be a purely virtual device
# 5) device should not be a CDROM
check_block_device() {
    local path=$1

    # Skip devices with zero capacity. This catches unattached loop*.
    [[ $(<$path/size) > 0 ]] || return 1

    # Skip read-only devices
    [[ $(<$path/ro) == 0 ]] || return 1

    # Skip non-removable devices; we're only interested in usb sticks.
    [[ $(<$path/removable) != 0 ]] || return 1

    # Skip virtual devices (/dev/loop? devices)
    [[ -d $path/device/block ]] || return 1

    # Skip CDROMs (cdrom devices have a ID_CDROM property)
    /sbin/udevadm info --query=property --path=$path | grep --silent ID_CDROM && return 1

    return 0
}

print_devices_and_die () {
    print_usage
    echo
    echo "The following block devices are valid:"
    for path in /sys/block/*; do
        check_block_device $path || continue

        local block_path=$(/sbin/udevadm info -r --query=name --path=$path)
        echo "  $block_path"
    done
    exit 0
}

verify_continue () {
    if $ASK_FIRST ; then
        echo "WARNING: $(basename $0) is not an NI supported script and is for internal use only."
        echo
        echo "If you proceed, $1 will have all data irreparably erased."
        read -p "Do you want to continue (y/N) ? " yn
        echo
        if [[ ! $yn =~ ^[Yy]+$ ]] ; then
            return 1
        fi
    fi

    return 0
}

# Check command line options
while getopts "i:lhy" opt; do
   case "$opt" in
   y )  ASK_FIRST=false ;;
   l )  print_devices_and_die ;;
   i )  IMAGE_FILE="$OPTARG" ;; 
   h )  print_usage_and_die 0 ;;
   esac
done
shift $(($OPTIND - 1))


# Check args
target=${1:-}
[ -z $target ] && print_usage_and_die 0

# Check paramter format (should be /dev/<dev>)
[ -z ${target##/dev/} ] && error_and_die "Unexpected paramter, expected device path (ie /dev/sdX)"

shift
[ "$#" -gt 0 ] && error_and_die "Target should be the final argument - invalid argument(s): $*"

# Verify boot image file is available
[ -f "$IMAGE_FILE" ] || error_and_die "File not found: $IMAGE_FILE"

# Verify the selected device passes the requrements (no formatting hard drives)
check_block_device /sys/block/${target##/dev/} || error_and_die "Selected device $target is not valid."

verify_continue $target || error_and_die "Aborted!"

echo "Partitioning and formating $target"
disk_setup $target >/dev/null 2>&1 || error_and_die "You may need root permission for formatting/partitioning the usb device."

echo "Copying files to $target (this will take a few minutes)"

# Create temporary mount point
readonly A_MOUNT=$(mktemp -d "/tmp/niboota-XXXXXXX")
mount "${target}1" ${A_MOUNT}

# Extract the boot image onto the USB (niboota partition)
# No need to waste time extracting to nibootb since the first
# boot will mirror niboota onto nibootb
tar xf ${IMAGE_FILE} -C ${A_MOUNT}

# Duplicate the /efi/nilrt dir to /efi/boot to enable UEFI-auto booting
cp -R ${A_MOUNT}/efi/* ${A_MOUNT}/efi/boot

# unmount target
umount ${A_MOUNT}

echo "DONE"
