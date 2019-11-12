#!/bin/bash
set -euo pipefail

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

print_usage_and_die () {
    echo >&2 'Usage: $0 -h'
    echo >&2 '   or: $0 -n <name> -r <recipe name> -d <disk size> -m <memory> [-i <images dir>] [-a <answer file>] [-q] [-v]'
    echo >&2 ''
    echo >&2 'Build a virtual machine with the given disk size and ram size from'
    echo >&2 'the specified bitbake recipe (which must be an image recipe).'
    echo >&2 ''
    echo >&2 'Must be run from the bitbake build directory.'
    echo >&2 'MACHINE env must be defined (ie export MACHINE x64).'
    echo >&2 ''
    echo >&2 '  -n <vm name>'
    echo >&2 '  -r <recipe name of an initramfs for the ISO to boot>'
    echo >&2 '  -d <boot disk size in MB>'
    echo >&2 '  -m <ram size in MB>'
    echo >&2 '  -i <images dir>'
    echo >&2 '  -a <answer file>'
    echo >&2 '  -q only build the qemu image (skip the other VM types)'
    echo >&2 '  -v verbose mode'
    exit 1
}

readonly SCRIPT_RESOURCE_DIR="`dirname "$BASH_SOURCE[0]"`/buildVM-files"

# get args
vmName=""
initramfsRecipeName=""
bootDiskSizeMB=""
memSizeMB=""
qemuOnly=0
answerFile=""
verbose_mode=0
imagesDir=""

while getopts "i:n:r:d:m:h:a:qv" opt; do
   case "$opt" in
   n )  vmName="$OPTARG" ;;
   r )  initramfsRecipeName="$OPTARG" ;;
   d )  bootDiskSizeMB="$OPTARG" ;;
   m )  memSizeMB="$OPTARG" ;;
   i )  imagesDir="$OPTARG" ;;
   a )  answerFile="$OPTARG" ;;
   q )  qemuOnly=1 ;;
   v )  verbose_mode=1 ;;
   h )  print_usage_and_die ;;
   \?)  print_usage_and_die ;;
   esac
done
shift $(($OPTIND - 1))

if [ "$verbose_mode" -eq 0 ] ; then
    do_silent() { "$@" &>/dev/null; }
else
    do_silent() { "$@"; }
fi

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
enableKVM=$(id | grep -q kvm && echo "-enable-kvm -cpu kvm64" || echo "")

isoImage="$imagesDir/$initramfsRecipeName-x64.iso"
[ ! -f $isoImage ] && isoImage="$imagesDir/$initramfsRecipeName-x64.wic"

do_silent qemu-system-x86_64 \
    $enableKVM -smp cpus=1 \
    -m "$memSizeMB" \
    -nographic \
    -drive if=pflash,format=raw,readonly,file="$vmDirQemu/OVMF/OVMF_CODE.fd" \
    -drive if=pflash,format=raw,file="$vmDirQemu/OVMF/OVMF_VARS.fd" \
    -drive file="$vmDirQemu/$vmName-$MACHINE.qcow2",index=0,media=disk \
    -drive file="$isoImage",index=1,media=cdrom,readonly \
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
    cp "$SCRIPT_RESOURCE_DIR/deprecated.txt" "$otherVmDir"
}

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

if [[ $qemuOnly -eq 0 ]] ; then
    mkdir "$baseVmDir-virtualbox"
    mkdir "$baseVmDir-vmware"
    mkdir "$baseVmDir-hyperv"

    chmod 0444 "$vmDirQemu/$vmName-$MACHINE.qcow2"
    build_alt_vmdisk  "vdi"   "$baseVmDir-virtualbox"
    build_alt_vmdisk  "vmdk"  "$baseVmDir-vmware"
    build_alt_vmdisk  "vhdx"  "$baseVmDir-hyperv"
    chmod 0644 "$vmDirQemu/$vmName-$MACHINE.qcow2"

    add_machine_def "virtualbox" "machine-def-$MACHINE.vbox" "$vmName-$MACHINE.vbox" 0644
    add_machine_def "vmware"     "machine-def-$MACHINE.vmx"  "$vmName-$MACHINE.vmx"  0644

    build_archive "virtualbox"
    build_archive "vmware"
    build_archive "hyperv"
fi
add_machine_def "qemu" "runQemuVM.sh"  "run-$vmName-$MACHINE.sh"  0755
add_machine_def "qemu" "runQemuVM.bat" "run-$vmName-$MACHINE.bat" 0755
build_archive   "qemu"

echo "DONE"
