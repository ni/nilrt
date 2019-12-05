#!/bin/bash
set -euo pipefail

cleanup() {
    local exitCode="$?"
    [ "$WAIT_PID" -eq 0 ] || kill -- -$$
    exit "$exitCode"
}

handle_err() {
    TMP_EVAL=`eval echo $5`

    echo "$1:$2 (fn=$3): Unexpected status code $4, while running command: '$TMP_EVAL'"
    exit $4
}

error_and_die() {
    echo >&2 "ERROR: $1"
    exit 1
}

print_usage_and_die() {
    echo >&2 "Usage: $0 -h | -p <path to ISO images> -i <path to ipk files> [-v]"
    echo >&2 ' It is recommended to run this script from the nilrt/build directory because it generates a directory of working files.'
    exit 1
}

# required by the buildVM.sh script
export MACHINE=x64

WAIT_PID=0
verbose_mode=0

readonly SCRIPT_DIR=$(dirname "$BASH_SOURCE[0]")
readonly SCRIPT_RESOURCE_DIR="$SCRIPT_DIR/provisioningTest-files"
readonly QEMU_NET_OPTS="-netdev user,hostfwd=tcp::2222-:22,id=provssh -device e1000,netdev=provssh"

while getopts "i:p:h:v" opt; do
    case "$opt" in
    p )  imageIsoPath="$OPTARG" ;;
    i )  ipkPath="$OPTARG" ;;
    v )  verbose_mode=1 ;;
    h )  print_usage_and_die ;;
    \?)  print_usage_and_die ;;
    esac
done
shift $(($OPTIND - 1))

readonly workingDir="./provisioningTest-working-dir"
readonly restoreModeImageIsoPath="${imageIsoPath:-}/restore-mode-image-$MACHINE.iso"
readonly safemodeRestoreImageIsoPath="${imageIsoPath:-}/safemode-restore-image-$MACHINE.iso"
readonly efiabVmName="provisioningTest-efi-ab"
readonly grubVmName="provisioningTest-grub"
readonly sshunsafeopts="-o ConnectTimeout=300 -o TCPKeepAlive=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
readonly sshopts="-p 2222 -i $workingDir/ssh_key $sshunsafeopts"
readonly scpopts="-P 2222 -i $workingDir/ssh_key $sshunsafeopts"

trap cleanup EXIT
trap 'handle_err ${BASH_SOURCE} ${LINENO} ${FUNCNAME:-unknown} $? "$BASH_COMMAND"' ERR

# SSH host-port lock vars for NILRT VMs
readonly LOCK_PORT=100
readonly LOCK_PORT_TIMEOUT=300

do_background() { "$@" &>>"$workingDir"/output-bg.log & }

if [ "$verbose_mode" -eq 0 ] ; then
    do_silent() { echo "$@">>"$workingDir"/output.log; "$@" &>>"$workingDir"/output.log; }
else
    do_silent() { echo "$@"; "$@"; }
fi

# 1: sshlogin; like 'root@localhost'
# 2: ssh command string
# 3: max retries (optional)
# 4: retry interval (optional)
do_silent_ssh() {
    local retries=0
    local max_retries=${3:-5}
    local retry_interval=${4:-5}

    while [ $retries -lt $max_retries ]; do
        ssh "${1}" $sshopts "${2}" &>>"$workingDir"/output.log && break || let "retries+=1"
        echo "  SSH command failed, retrying (${retries}/${max_retries}) shell command: ${2}"
        sleep $retry_interval
    done

    [ $retries -lt $max_retries ] || (echo "SSH Max retries exceeded" && exit 1)
}

background_vm() {
    echo "  Starting background VM: $1"
    flock --wait "$LOCK_PORT_TIMEOUT" $LOCK_PORT
    do_background "$workingDir"/"$1"-"$MACHINE"-qemu/run-"$1"-"$MACHINE".sh -- $QEMU_NET_OPTS
    WAIT_PID=$!
    sleep 30
}

# 1: pexpect script name
# 2: vm name
pexpect_vm() {
    local pexpect_script="$1"
    local vm_name="$2"

    echo "  Starting foreground VM: $vm_name with pexpect: $pexpect_script"
    flock --wait $LOCK_PORT_TIMEOUT $LOCK_PORT
    do_silent "$SCRIPT_RESOURCE_DIR/${pexpect_script}.expect" "$workingDir"/"$vm_name"-"$MACHINE"-qemu/run-"$vm_name"-"$MACHINE".sh
    flock --unlock $LOCK_PORT
}

setupSsh_efi_ab() {
    echo "  Enable ssh pubkey login (efi-ab)"

    # Install ssh public key
    do_silent_ssh root@localhost 'mkdir -p -m 700 ~/.ssh'
    cat "$workingDir"/ssh_key.pub | do_silent_ssh root@localhost 'cat >>.ssh/authorized_keys'
}

setupSsh_grub() {
    echo "  Enable ssh pubkey login (grub)"

    # Install ssh public key
    do_silent_ssh admin@localhost 'mkdir -p -m 700 ~/.ssh'
    cat "$workingDir"/ssh_key.pub | do_silent_ssh admin@localhost 'cat >>.ssh/authorized_keys'
}

shutdownSsh() {
    echo "  Shutdown VM"
    # Shutdown the VM
    do_silent_ssh root@localhost 'halt'

    # Wait for process to shutdown completely
    wait $WAIT_PID && WAIT_PID=0 # Verify VM shuts down cleanly
    flock -u "$LOCK_PORT"
}

validate_efi_ab_partitions() {
    local lsblk_data=$(ssh root@localhost $sshopts -C 'lsblk -lno NAME,LABEL,FSTYPE,MOUNTPOINT /dev/sda' 2>/dev/null)

    echo "  Validate efi-ab partition layout"
    # Check the partition labels, file system type, and mount point
    echo "$lsblk_data" | grep niboota |grep vfat |grep -q '/boot'
    echo "$lsblk_data" | grep nibootb |grep -q vfat
    echo "$lsblk_data" | grep niuser  |grep -q ext4
}

validate_grub_partitions() {
    local lsblk_data=$(ssh root@localhost $sshopts -C 'lsblk -lno NAME,LABEL,FSTYPE,MOUNTPOINT /dev/sda' 2>/dev/null)

    echo "  Validate grub partition layout"
    # Check the partition labels, file system type, and mount point
    echo "$lsblk_data" | grep nigrub   |grep -q vfat
    echo "$lsblk_data" | grep nibootfs |grep ext4 |egrep -q '/boot$'
    echo "$lsblk_data" | grep niconfig |grep ext4 |egrep -q '/mnt/userfs/etc/natinst/share$'
    echo "$lsblk_data" | grep nirootfs |grep ext4 |egrep -q '/mnt/userfs$'
}

install_efi_ab_gateway() {
    echo "  Install efi-ab gateway ipk"
    
    # copy ipk from build directory
    do_silent scp $scpopts "$ipkPath"/dist-nilrt-efi-ab-gateway_*.ipk root@localhost:dist-nilrt-efi-ab-gateway.ipk

    # install the ipk
    do_silent_ssh root@localhost 'opkg install dist-nilrt-efi-ab-gateway.ipk && /usr/share/nilrt/nilrt-install'
}

install_grub_gateway() {
    echo "  Install grub gateway ipk"

    # copy ipk from build directory
    do_silent scp $scpopts "$ipkPath"/dist-nilrt-grub-gateway_*.ipk root@localhost:dist-nilrt-grub-gateway.ipk

    # opkg install the dist ipk
    do_silent_ssh root@localhost 'opkg install dist-nilrt-grub-gateway.ipk && /usr/share/nilrt/nilrt-install'
}

# check env
[ -d "${imageIsoPath:-}" ] || error_and_die 'Must specify ISO image path with -p. Run with -h for help.'
[ -d "${ipkPath:-}" ] || error_and_die 'Must specify ipk path with -i. Run with -h for help.'
[ -e "$restoreModeImageIsoPath" ] || error_and_die "$restoreModeImageIsoPath does not exist."
[ -e "$safemodeRestoreImageIsoPath" ] || error_and_die "$safemodeRestoreImageIsoPath does not exist."
[ -e "$ipkPath"/dist-nilrt-efi-ab-gateway_*.ipk ] || error_and_die "$ipkPath/dist-nilrt-efi-ab-gateway_*.ipk does not exist."
[ -e "$ipkPath"/dist-nilrt-grub-gateway_*.ipk ] || error_and_die "$ipkPath/dist-nilrt-grub-gateway_*.ipk does not exist."

# clean working dir
rm -Rf "$workingDir"
[ ! -e "$workingDir" ]
mkdir -p "$workingDir"
echo "Built empty working dir at $workingDir"

# establish SSH host-port lock for use by NILRT VMs
exec 100>"${workingDir}"/socket-ssh-redirect.lock

# Run buildVM.sh script with a timeout to create images
echo "Deploy efi-ab and grub images to blank hard drives."
echo "  Create efi-ab virtual machine"
do_silent timeout 200 $SCRIPT_DIR/buildVM.sh -d 10240 -m 2048 -n "$efiabVmName" -r restore-mode-image -q -i "$imageIsoPath" -a "$SCRIPT_RESOURCE_DIR"/ni_provisioning.answers
echo "  Create grub virtual machine"
do_silent timeout 200 $SCRIPT_DIR/buildVM.sh -d 10240 -m 2048 -n "$grubVmName" -r safemode-restore-image -q -i "$imageIsoPath" -a "$SCRIPT_RESOURCE_DIR"/ni_provisioning.answers


# Move the VMs to the working directory and unzip them
mv "$imageIsoPath"/provisioningTest-*.zip "$workingDir"
do_silent unzip -d "$workingDir" "$workingDir"'/*.zip'


#
# Launch both newly provisioned VMs to verify that they load without panic, etc.  This test fails
# if the expect script gets a timeout, which indicates the login prompt never appeared or shutdown
# took to long to complete.
#
echo "Launch both images and validate they boot to login screen and shutdown."


# Launch the efi-ab VM, login and shutdown
echo "  Launch, login, and shutdown efi-ab virtual machine"
pexpect_vm "efi-ab" "$efiabVmName"
# Launch the grub VM, login, enable ssh, and shutdown
echo "  Launch, login, enable ssh, and shutdown grub virtual machine"
pexpect_vm "grub" "$grubVmName"


#
# Check partition layouts for each of the virtual machines and verify they are partitioned and named
# as expected.
#

# Generate set of ssh keys to use instead of user/password
rm -fr "$workingDir"/ssh_key*
do_silent ssh-keygen -t rsa -b 2048 -f "$workingDir"/ssh_key -q -N ''

echo "Validate efi-ab vm, install grub-gateway, and validate grub vm"
background_vm "$efiabVmName"
setupSsh_efi_ab
validate_efi_ab_partitions
install_grub_gateway
shutdownSsh
echo "  Validate grub-gateway install completes"
pexpect_vm "grub" "$efiabVmName"
echo "  Relaunch the efi-ab VM, but expect grub layout"
background_vm "$efiabVmName"
setupSsh_grub
validate_grub_partitions
shutdownSsh

echo "Validate grub vm, install efi-ab-gateway, and validate efi-ab vm"
background_vm "$grubVmName"
setupSsh_grub
validate_grub_partitions
install_efi_ab_gateway
shutdownSsh
echo "  Validate efi-ab gateway install completes"
pexpect_vm "efi-ab" "$grubVmName"
echo "  Relaunch the grub VM, but expect efi-ab layout"
background_vm "$grubVmName"
setupSsh_efi_ab
validate_efi_ab_partitions
shutdownSsh

echo 'Test passed!'
