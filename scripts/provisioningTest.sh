#!/bin/bash
set -e

error_and_die() {
    echo >&2 "ERROR: $1"
    exit 1
}

print_usage_and_die() {
    echo >&2 "Usage: $0 -h | -r <path to restore mode image ISO>"
    echo >&2 ' It is recommended to run this script from the nilrt/build directory because it generates a directory of working files.'
    exit 1
}

SCRIPT_RESOURCE_DIR="`dirname "$BASH_SOURCE[0]"`/provisioningTest-files"

while getopts "n:r:d:m:h" opt; do
    case "$opt" in
    r )  restoreModeImageIsoPath="$OPTARG" ;;
    h )  print_usage_and_die ;;
    \?)  print_usage_and_die ;;
    esac
done
shift $(($OPTIND - 1))

# check env
[ -n "$restoreModeImageIsoPath" ] || error_and_die 'Must specify restore mode image ISO path with -r. Run with -h for help.'
[ -e "$restoreModeImageIsoPath" ] || error_and_die '$restoreModeImageIsoPath does not exist. Must provide a valid restore mode image ISO.'

workingDir="./provisioningTest-working-dir"

# clean working dir
rm -Rf "$workingDir"
[ ! -e "$workingDir" ]
mkdir -p "$workingDir"
echo "Built empty working dir at $workingDir"

mkdir "$workingDir/before"
mkdir "$workingDir/after"
echo blah > "$workingDir/testfile_sda1.txt"
echo blah > "$workingDir/testfile_sda2.txt"
echo blah > "$workingDir/testfile_sda3.txt"
echo blah > "$workingDir/testfile_sda4.txt"

qemu-img create -f qcow2 "$workingDir/test-image.qcow2" 2G
qemu-img snapshot -c "empty" "$workingDir/test-image.qcow2"
echo "Built empty disk image"

guestfish --pipe-error -a "$workingDir/test-image.qcow2" <<_EOF_
run
part-init /dev/sda gpt
part-add /dev/sda p 128 40960
part-add /dev/sda p 40961 81920
part-add /dev/sda p 81921 122880
part-add /dev/sda p 122881 2097152
mkfs vfat /dev/sda1 label:part1
mkfs ext3 /dev/sda2 label:part2
mkfs ext4 /dev/sda3 label:part3
mkfs ext4 /dev/sda4 label:part4
part-get-gpt-guid /dev/sda 4 | tee "$workingDir/before/sda4_partition_uuid.txt"
vfs-uuid /dev/sda4 | tee "$workingDir/before/sda4_filesystem_uuid.txt"
mount /dev/sda1 /
copy-in "$workingDir/testfile_sda1.txt" /
sync
ls / | tee "$workingDir/before/sda1_contents.txt"
umount /dev/sda1
mount /dev/sda2 /
copy-in "$workingDir/testfile_sda2.txt" /
sync
ls / | tee "$workingDir/before/sda2_contents.txt"
umount /dev/sda2
mount /dev/sda3 /
copy-in "$workingDir/testfile_sda3.txt" /
sync
ls / | tee "$workingDir/before/sda3_contents.txt"
umount /dev/sda3
mount /dev/sda4 /
copy-in "$workingDir/testfile_sda4.txt" /
sync
ls / | tee "$workingDir/before/sda4_contents.txt"
umount /dev/sda4
shutdown
quit
_EOF_
wait
qemu-img snapshot -c "ready-for-test" "$workingDir/test-image.qcow2"
echo "Prepared disk image for testing"

read nilrt_partition_uuid < "$workingDir/before/sda4_partition_uuid.txt"
read nilrt_filesystem_uuid < "$workingDir/before/sda4_filesystem_uuid.txt"

create_answer_file_iso_image() {
    local nilrt_partition_id_value="$1"

    if [ -e "$workingDir/ni_provisioning.answers" ] ; then
        chmod 0664 "$workingDir/ni_provisioning.answers"
    fi
    if [ -e "$workingDir/ni_provisioning.answers.iso" ] ; then
        chmod 0664 "$workingDir/ni_provisioning.answers.iso"
    fi
    rm -f "$workingDir/ni_provisioning.answers"
    cp "$SCRIPT_RESOURCE_DIR/ni_provisioning.answers" "$workingDir/ni_provisioning.answers"
    sed -i -e "s/CHANGE_THIS_ID/$nilrt_partition_id_value/g" "$workingDir/ni_provisioning.answers"
    sed -i -e "s/CHANGE_THIS_LABEL/testlabel/g" "$workingDir/ni_provisioning.answers"
    chmod 0444 "$workingDir/ni_provisioning.answers"
    genisoimage -full-iso9660-filenames -o "$workingDir/ni_provisioning.answers.iso" "$workingDir/ni_provisioning.answers"
    chmod 0444 "$workingDir/ni_provisioning.answers.iso"
    echo "Built answers file at $workingDir/ni_provisioning.answers.iso"
}

run_provisioning_tool() {
    qemu-system-x86_64 \
        -m 1024 \
        -boot d \
        -nographic \
        -drive file="$workingDir/test-image.qcow2",index=0,media=disk \
        -drive file="$restoreModeImageIsoPath",index=1,media=cdrom,readonly \
        -drive file="$workingDir/ni_provisioning.answers.iso",index=2,media=cdrom,readonly
    echo "Completed the provisioning operation"
}

validate_provisioning() {
    local compare_filesystem_uuids="$1"

    guestfish --pipe-error -a "$workingDir/test-image.qcow2" <<_EOF_
    run
    mount /dev/sda1 /
    ls / | tee "$workingDir/after/sda1_contents.txt"
    umount /dev/sda1
    mount /dev/sda2 /
    ls / | tee "$workingDir/after/sda2_contents.txt"
    umount /dev/sda2
    mount /dev/sda3 /
    ls / | tee "$workingDir/after/sda3_contents.txt"
    umount /dev/sda3
    mount /dev/sda4 /
    ls / | tee "$workingDir/after/sda4_root_contents.txt"
    ls /boot | tee "$workingDir/after/sda4_boot_contents.txt"
    ls /sbin | tee "$workingDir/after/sda4_sbin_contents.txt"
    vfs-label /dev/sda4 | tee "$workingDir/after/sda4_filesystem_label.txt"
    part-get-gpt-guid /dev/sda 4 | tee "$workingDir/after/sda4_partition_uuid.txt"
    vfs-uuid /dev/sda4 | tee "$workingDir/after/sda4_filesystem_uuid.txt"
    copy-out /boot/grub/grubenv "$workingDir/after"
    umount /dev/sda4
    unmount-all
    shutdown
    quit
_EOF_
    wait
    echo "Inspected disk image after provisioning operation"

    cmp -s "$workingDir/before/sda1_contents.txt" "$workingDir/after/sda1_contents.txt"
    cmp -s "$workingDir/before/sda2_contents.txt" "$workingDir/after/sda2_contents.txt"
    cmp -s "$workingDir/before/sda3_contents.txt" "$workingDir/after/sda3_contents.txt"
    ! grep testfile_sda4.txt "$workingDir/after/sda4_root_contents.txt"
    grep README_File_Paths.txt "$workingDir/after/sda4_root_contents.txt"
    grep bzImage "$workingDir/after/sda4_boot_contents.txt"
    grep init "$workingDir/after/sda4_sbin_contents.txt"
    test "testlabel" = "$(cat $workingDir/after/sda4_filesystem_label.txt)"
    cmp -s "$workingDir/before/sda4_partition_uuid.txt" "$workingDir/after/sda4_partition_uuid.txt"
    # only want to check this when testing with filesystem UUID
    if $compare_filesystem_uuids; then
        cmp -s "$workingDir/before/sda4_filesystem_uuid.txt" "$workingDir/after/sda4_filesystem_uuid.txt"
    fi
    grep -i "root_partition_name=PARTUUID=$nilrt_partition_uuid" "$workingDir/after/grubenv"
    echo "Validated disk image after restore operation"
}

create_answer_file_iso_image "UUID=$nilrt_filesystem_uuid"
run_provisioning_tool
validate_provisioning "true"
qemu-img snapshot -a "ready-for-test" "$workingDir/test-image.qcow2"
create_answer_file_iso_image "PARTUUID=$nilrt_partition_uuid"
run_provisioning_tool
validate_provisioning "false"
qemu-img snapshot -a "ready-for-test" "$workingDir/test-image.qcow2"
create_answer_file_iso_image "LABEL=part4"
run_provisioning_tool
validate_provisioning "false"
