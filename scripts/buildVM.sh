#!/bin/bash
set -euo pipefail

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

print_usage_and_die () {
    local rc=${1:-2}
    if [ $rc -ne 0 ]; then
        exec 1>&2
    fi
    cat <<EOF
buildVM.sh -h
  Print this help message and exit
buildVM.sh -n name -r recipe_name -d disk_size -m memory \\
           [-a answer_file] [-i images_dir] [-v]
  Create a NILRT virtual machine archive (QEMU).

Arguments:
  -a answer_file  Use the answer file at answer_file, instead of the default.
  -d disk_size    The size of the built-VM qcow2 disk (in GB)
  -h              Print this help message and exit.
  -i images_dir   The location of the bitbake images deploy dir
                  Default: ./tmp-glibc/deploy/images/\$MACHINE
  -m memory       The virtual memory size (in MB), for the VM
                  (during provisioning)
  -n name         The name of the final VM archive
  -r recipe_name  The name of the recovery media ISO, within the images_dir
                  Example: \`foo-bar-x64.iso\` has recipe_name: \`foo-bar\`
EOF
    exit $rc
}

readonly SCRIPT_RESOURCE_DIR="`dirname "$BASH_SOURCE[0]"`/buildVM-files"
readonly MACHINE=x64

# get args
vmName=""
initramfsRecipeName=""
bootDiskSizeMB=""
memSizeMB=""
answerFile=""
imagesDir=""

while getopts "i:n:r:d:m:a:h" opt; do
   case "$opt" in
   a )  answerFile="$OPTARG" ;;
   d )  bootDiskSizeMB="$OPTARG" ;;
   h )  print_usage_and_die 0 ;;
   i )  imagesDir="$OPTARG" ;;
   m )  memSizeMB="$OPTARG" ;;
   n )  vmName="$OPTARG" ;;
   r )  initramfsRecipeName="$OPTARG" ;;
   \?)  print_usage_and_die ;;
   esac
done
shift $(($OPTIND - 1))

[ -n "$vmName" ] || error_and_die 'Must specify VM name with -n. Run with -h for help.'
[ -n "$initramfsRecipeName" ] || error_and_die 'Must specify recipe name with -r. Run with -h for help.'
[ -n "$bootDiskSizeMB" ] || error_and_die 'Must specify boot disk size with -d (in MB). Run with -h for help.'
[ -n "$memSizeMB" ] || error_and_die 'Must specify memory size with -m (in MB). Run with -h for help.'

# check env
readonly workingDir="./buildVM-working-dir"

[ -n "$MACHINE" ] || error_and_die 'No MACHINE specified in env'
[ -z "$imagesDir" ] && imagesDir="./tmp-glibc/deploy/images/$MACHINE"
[ -d "$imagesDir" ] || error_and_die "$imagesDir does not exist. This script must be run from the build directory."

baseVmDir="$workingDir/$vmName-$MACHINE"
vmDirQemu="$baseVmDir-qemu"

# clean working dir
rm -Rf "$workingDir"
[ ! -e "$workingDir" ]
mkdir -p "$workingDir"
echo "Built empty working dir at $workingDir"

# add hypervisor-specific dirs
mkdir "$vmDirQemu"

# create answer file iso image
[ -z "$answerFile" ] && answerFile="$SCRIPT_RESOURCE_DIR/ni_provisioning.answers"
cp "$answerFile" "$workingDir/ni_provisioning.answers"
chmod 0444 "$workingDir/ni_provisioning.answers"
genisoimage -quiet -input-charset utf-8 -full-iso9660-filenames -o "$workingDir/ni_provisioning.answers.iso" "$workingDir/ni_provisioning.answers"
chmod 0444 "$workingDir/ni_provisioning.answers.iso"
echo "Built answers file at $workingDir/ni_provisioning.answers.iso using $answerFile"

# Copy OVMF UEFI files for qemu
cp -r "$SCRIPT_RESOURCE_DIR/OVMF" "$vmDirQemu/"

# build qcow2 disk (for qemu) by booting NILRT restore disk to
#  partition and install OS
qemu-img create -q -f qcow2 "$vmDirQemu/$vmName-$MACHINE.qcow2" "$bootDiskSizeMB""M"
chmod 0644 "$vmDirQemu/$vmName-$MACHINE.qcow2"

# Enable the KVM hypervisor layer, if it seems like it is supported.
if [ -w /dev/kvm ]; then
    echo "INFO: /dev/kvm detected as writable. Enabling KVM hypervisor."
    enableKVM="-enable-kvm"
else
    echo "INFO: /dev/kvm is not writable. KVM will not be enabled."
fi

isoImage="$imagesDir/$initramfsRecipeName-x64.iso"
[ ! -f $isoImage ] && isoImage="$imagesDir/$initramfsRecipeName-x64.wic"

qemu-system-x86_64 \
    ${enableKVM:-} -cpu qemu64 -smp cpus=1 \
    -m "$memSizeMB" \
    -nographic \
    -drive if=pflash,format=raw,readonly,file="$vmDirQemu/OVMF/OVMF_CODE.fd" \
    -drive if=pflash,format=raw,file="$vmDirQemu/OVMF/OVMF_VARS.fd" \
    -drive file="$vmDirQemu/$vmName-$MACHINE.qcow2",index=0,media=disk \
    -drive file="$isoImage",index=1,media=cdrom,readonly \
    -drive file="$workingDir/ni_provisioning.answers.iso",index=2,media=cdrom,readonly \
# end qemu-system-x86_64

echo "Built qcow2 disk at $vmDirQemu/$vmName-$MACHINE.qcow2"

# add machine definition files
function add_machine_def()
{
    local hypervisorName="$1"
    local srcMachineDefFileName="$2"
    local dstMachineDefFileName="$3"
    local dstMachineDefPerm="$4"
    local archiveDirName="$vmName-$MACHINE-$hypervisorName"
    local vmMachineUuid="`uuidgen`"
    local vmDiskUuid=""
    cp "$SCRIPT_RESOURCE_DIR/$srcMachineDefFileName" "$workingDir/$archiveDirName/$dstMachineDefFileName"
    chmod "$dstMachineDefPerm" "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_NAME}/$vmName-$MACHINE/g"           "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_MACHINE_UUID}/$vmMachineUuid/g"     "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_DISK_UUID}/$vmDiskUuid/g"           "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_MEM_SIZE_MB}/$memSizeMB/g"          "$workingDir/$archiveDirName/$dstMachineDefFileName"
    echo "Wrote $hypervisorName machine def file $workingDir/$archiveDirName/$dstMachineDefFileName"
}

# pack archives for qemu, virtualbox, vmware, and hyperv
function build_archive()
{
    local hypervisorName="$1"
    local archiveDirName="$vmName-$MACHINE-$hypervisorName"
    local archiveName="$archiveDirName.zip"
    (cd "$workingDir" && zip --quiet -r "$archiveName" "$archiveDirName" && chmod 444 "$archiveName")
    rm -f "$imagesDir/$archiveName"
    [ ! -e "$imagesDir/$archiveName" ]
    mv "$workingDir/$archiveName" "$imagesDir/$archiveName"
    echo "Saved $hypervisorName archive to $imagesDir/$archiveName"
}

add_machine_def "qemu" "runQemuVM.sh"  "run-$vmName-$MACHINE.sh"  0755
add_machine_def "qemu" "runQemuVM.bat" "run-$vmName-$MACHINE.bat" 0755
build_archive   "qemu"

echo "DONE"
