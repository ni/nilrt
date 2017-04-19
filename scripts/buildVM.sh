#!/bin/bash
set -e

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

print_usage_and_die () {
    echo >&2 "Usage: $0 -h | -n <vm name> -r <recipe name of an initramfs for the ISO to boot> -d <boot disk size in MB> -m <ram size in MB>"
    echo >&2 ' Must be run from a bitbake environment.'
    echo >&2 ' MACHINE env must be defined.'
    exit 1
}

SCRIPT_RESOURCE_DIR="`dirname "$BASH_SOURCE[0]"`/buildVM-files"

# get args
vmName=""
initramfsRecipeName=""
bootDiskSizeMB=""
memSizeMB=""

while getopts "n:r:d:m:h" opt; do
   case "$opt" in
   n )  vmName="$OPTARG" ;;
   r )  initramfsRecipeName="$OPTARG" ;;
   d )  bootDiskSizeMB="$OPTARG" ;;
   m )  memSizeMB="$OPTARG" ;;
   h )  print_usage_and_die ;;
   \?)  print_usage_and_die ;;
   esac
done
shift $(($OPTIND - 1))

[ -n "$vmName" ] || error_and_die 'Must specify VM name with -n. Run with -h for help.'
[ -n "$initramfsRecipeName" ] || error_and_die 'Must specify recipe name with -r. Run with -h for help.'
[ -n "$bootDiskSizeMB" ] || error_and_die 'Must specify boot disk size with -d (in MB). Run with -h for help.'
[ -n "$memSizeMB" ] || error_and_die 'Must specify memory size with -m (in MB). Run with -h for help.'

# check env
[ -n "$MACHINE" ] || error_and_die 'No MACHINE specified in env'
bitbake --parse-only >/dev/null || error_and_die 'Bitbake failed. Check your environment. This script must be run from the build directory.'

imagesDir="./tmp-glibc/deploy/images/$MACHINE"
[ -d "$imagesDir" ] || error_and_die '$imagesDir does not exist. Need to build a bootable image first.'

workingDir="./buildVM-working-dir"
baseVmDir="$workingDir/$vmName-$MACHINE"
vmDirQemu="$baseVmDir-qemu"

# clean working dir
rm -Rf "$workingDir"
[ ! -e "$workingDir" ]
mkdir -p "$workingDir"
echo "Built empty working dir at $workingDir"

# add hypervisor-specific dirs
mkdir "$vmDirQemu"
mkdir "$baseVmDir-virtualbox"
mkdir "$baseVmDir-vmware"
mkdir "$baseVmDir-hyperv"

# create answer file iso image
rm -f "$workingDir/ni_provisioning.answers"
cp "$SCRIPT_RESOURCE_DIR/ni_provisioning.answers" "$workingDir/ni_provisioning.answers"
chmod 0444 "$workingDir/ni_provisioning.answers"
genisoimage -full-iso9660-filenames -o "$workingDir/ni_provisioning.answers.iso" "$workingDir/ni_provisioning.answers"
chmod 0444 "$workingDir/ni_provisioning.answers.iso"
echo "Built answers file at $workingDir/ni_provisioning.answers.iso"

# build qcow2 disk (for qemu) by booting NILRT restore disk to
#  partition and install OS
qemu-img create -f qcow2 "$vmDirQemu/$vmName-$MACHINE.qcow2" "$bootDiskSizeMB""M"
chmod 0644 "$vmDirQemu/$vmName-$MACHINE.qcow2"
qemu-system-x86_64 \
    -enable-kvm -cpu kvm64 -m "$memSizeMB" \
    -nographic \
    -drive file="$vmDirQemu/$vmName-$MACHINE.qcow2",index=0,media=disk \
    -drive file="$imagesDir/$initramfsRecipeName-x64.iso",index=1,media=cdrom,readonly \
    -drive file="$workingDir/ni_provisioning.answers.iso",index=2,media=cdrom,readonly \
    </dev/null
echo "Built qcow2 disk at $vmDirQemu/$vmName-$MACHINE.qcow2"

# build alt disk formats for virtualbox, vmware, and hyperv
function build_alt_vmdisk()
{
    local fmt="$1"
    local otherVmDir="$2"
    qemu-img convert -f qcow2 -O "$fmt" "$vmDirQemu/$vmName-$MACHINE.qcow2" "$otherVmDir/$vmName-$MACHINE.$fmt"
    if [[ $fmt == "vdi" ]]; then
        # virtualbox unfortunately requires unique UUIDs
        VBoxManage internalcommands sethduuid "$otherVmDir/$vmName-$MACHINE.$fmt"
    fi
}
chmod 0444 "$vmDirQemu/$vmName-$MACHINE.qcow2"
build_alt_vmdisk  "vdi"   "$baseVmDir-virtualbox"
build_alt_vmdisk  "vmdk"  "$baseVmDir-vmware"
build_alt_vmdisk  "vhdx"  "$baseVmDir-hyperv"
chmod 0644 "$vmDirQemu/$vmName-$MACHINE.qcow2"

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
    if [[ $hypervisorName == "virtualbox" ]]; then
        # virtualbox unfortunately requires a UUID reference in it's machine definition
        vmDiskUuid="`VBoxManage showhdinfo "$workingDir/$archiveDirName/$vmName-$MACHINE.vdi" | grep '^UUID: ' | tr -s ' ' | cut -d' ' -f2`"
    fi
    cp "$SCRIPT_RESOURCE_DIR/$srcMachineDefFileName" "$workingDir/$archiveDirName/$dstMachineDefFileName"
    chmod "$dstMachineDefPerm" "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_NAME}/$vmName-$MACHINE/g"           "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_MACHINE_UUID}/$vmMachineUuid/g"     "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_DISK_UUID}/$vmDiskUuid/g"           "$workingDir/$archiveDirName/$dstMachineDefFileName"
    sed -i "s/\${VM_MEM_SIZE_MB}/$memSizeMB/g"          "$workingDir/$archiveDirName/$dstMachineDefFileName"
    echo "Wrote $hypervisorName machine def file $workingDir/$archiveDirName/$dstMachineDefFileName"
}
add_machine_def  "qemu"        "runQemuVM.sh"               "run-$vmName-$MACHINE.sh"  0755
add_machine_def  "virtualbox"  "machine-def-$MACHINE.vbox"  "$vmName-$MACHINE.vbox"    0644
add_machine_def  "vmware"      "machine-def-$MACHINE.vmx"   "$vmName-$MACHINE.vmx"     0644

# pack archives for qemu, virtualbox, vmware, and hyperv
function build_archive()
{
    local hypervisorName="$1"
    local archiveDirName="$vmName-$MACHINE-$hypervisorName"
    local archiveName="$archiveDirName.zip"
    (cd "$workingDir" && zip -r "$archiveName" "$archiveDirName" && chmod 444 "$archiveName")
    rm -f "$imagesDir/$archiveName"
    [ ! -e "$imagesDir/$archiveName" ]
    mv "$workingDir/$archiveName" "$imagesDir/$archiveName"
    echo "Saved $hypervisorName archive to $imagesDir/$archiveName"
}
build_archive  "qemu"
build_archive  "virtualbox"
build_archive  "vmware"
build_archive  "hyperv"

echo "DONE"
