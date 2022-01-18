#!/bin/bash
set -euo pipefail

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))
SCRIPT_RESOURCE_DIR=$(realpath "${SCRIPT_ROOT}/vm-resources")

LOG_VERBOSEONLY_CHANNELS=(INFO)
log() {
	local log_level=$1
	local log_msg=${@:2}
	if [[ "${LOG_VERBOSEONLY_CHANNELS[@]}" == *"$log_level"* \
		&& "${verbose:-}" != true ]]; then
		return
	else
		echo "${log_level}:" $log_msg >&2
	fi
}


## CLI PARSING
usage() {
	cat <<EOF
$(basename ${BASH_SOURCE}) [--help] [--verbose] \\
    [-a ANSWER_FILE] [-d DISK_SIZE] [-m MEMORY] [-n NAME] [-r RECOVERY_ISO]

Create a NILRT virtual machine archive (QEMU).

# Options
-a,--answer-file ANSWER_FILE
    A path to a NILRT provisioning answers file.
-d,--disk-size DISK_SIZE
    The primary size of the VM's main storage device. Defaults to 4096 MB.
-m,--memory MEMORY_MB
	The desired size (in megabytes) for the VM's virtual RAM. Defaults to
    1024 MB.
-n,--name NAME
    The desired name for the VM archive. Defaults to 'nilrt'.
-r,--recovery-iso RECOVERY_ISO
	The filepath to the NILRT recovery media ISO, which will provision the
    primary disk.
EOF
}

RECOVERY_IMAGE_RECIPE_NAME=nilrt-recovery-media
PYREX_RUN=pyrex-run

DEFAULT_IMAGES_DIR="./tmp-glibc/deploy/images/x64"

answers_file="${SCRIPT_RESOURCE_DIR}/ni_provisioning.answers"
disk_size_mb=4096
memory_mb=1024
recovery_iso=
positionals=()
verbose=false
vm_name=nilrt
build_workspace="./build.vm.tmp"

while [ $# -ge 1 ]; do case "$1" in
	-h|--help)
		usage
		exit 0
		;;
	-a|--answers-file)
		shift
		if [ ! -e "$1" ]; then
			log ERROR "Answers file path $1 does not exist."
			exit 2
		fi
		answers_file=$(realpath "$1")
		shift
		;;
	-d|--disk-size)
		shift
		disk_size_mb=$1
		shift
		;;
	-m|--memory)
		shift
		memory_mb=$1
		shift
		;;
	-n|--name)
		shift
		vm_name=$1
		shift
		;;
	-r|--recovery-iso)
		shift
		recovery_iso=$(realpath $1)
		shift
		;;
	-v|--verbose)
		verbose=true
		shift
		;;
	-*|--*)
		log ERROR "Invalid or unknown option \"$1\"."
		exit 2
		;;
	*)
		positionals+=($1)
		shift
		;;
esac; done


## MAIN

archive_vm_dir() {
	local source_directory=$1

	local vm_dir_basename=$(basename $source_directory)
	local vm_archive=${vm_dir_basename}.zip

	zip --quiet -r \
		${vm_archive} \
		"$source_directory"
	chmod 0444 "${vm_archive}"

	log INFO "Created VM archive: ${vm_archive}"
}

# Create and provision a QEMU VM directory using content from the resource
# directory and the NIRLT recovery ISO at $recovery_iso.
build_qemu_vm() {
	local vm_fullname=$1
	local vm_workspace=$2

	mkdir -p "${vm_workspace}"

	pushd "${vm_workspace}" >/dev/null
	local primary_disk="${vm_fullname}.qcow2"

	# Copy OVMF UEFI files
	cp -r "$SCRIPT_RESOURCE_DIR/OVMF" .

	# Provision a qcow2 disk with NILRT using the recovery media ISO.
	$PYREX_RUN qemu-img create -q \
		-f qcow2 "./$vm_name-x64.qcow2" \
		"$disk_size_mb""M"
	chmod 0644 "./$vm_name-x64.qcow2"

	# Enable the KVM hypervisor layer, if it seems like it is supported.
	if $($PYREX_RUN test -w /dev/kvm); then
	    log INFO "/dev/kvm detected as writable; enabling KVM hypervisor."
	    enableKVM="-enable-kvm"
	else
	    log WARN "/dev/kvm is not writable; KVM will not be enabled."
	fi

	echo "Provisioning NILRT on QEMU VM..."
	$PYREX_RUN qemu-system-x86_64 \
		${enableKVM:-} -cpu qemu64 -smp cpus=1 \
		-m "$memory_mb" \
		-nographic \
		-drive if=pflash,format=raw,readonly=on,file="./OVMF/OVMF_CODE.fd" \
		-drive if=pflash,format=raw,file="./OVMF/OVMF_VARS.fd" \
		-drive file="./${vm_fullname}.qcow2",index=0,media=disk \
		-drive file="${recovery_iso}",index=1,media=cdrom,readonly=on \
		-drive file="$build_workspace/ni_provisioning.answers.iso",index=2,media=cdrom,readonly=on \
	# end qemu-system-x86_64

	write_vm_startup_script "runQemuVM.sh" "start-vm.sh" "$primary_disk"
	write_vm_startup_script "runQemuVM.bat" "start-vm.bat" "$primary_disk"

	popd >/dev/null
}

# Create an ISO file called "ni_provisioning.answers.iso" in the current
# working directory, which contains only the answers file at $answers_file.
create_answers_iso() {
	cp "$answers_file" "ni_provisioning.answers"
	chmod 0444 "ni_provisioning.answers"
	$PYREX_RUN genisoimage -quiet \
		-input-charset utf-8 \
		-full-iso9660-filenames \
		-o "ni_provisioning.answers.iso" \
		"ni_provisioning.answers"
	chmod 0444 "ni_provisioning.answers.iso"
	log DEBUG "Built answers file at $(realpath ./ni_provisioning.answers.iso) using $answers_file."
}

error_and_die () {
	log ERROR $1
	exit 1
}

# Copies a vm startup script template from the resource directory into the CWD,
# and replaces template values with those relevant to the VM.
write_vm_startup_script() {
	local script_template=$1
	local script_destination_path=$2
	local primary_disk=$3

	install \
		--mode=0755 \
		"${SCRIPT_RESOURCE_DIR}/${script_template}" \
		"./${script_destination_path}"

	sed -i "s%\${PRIMARY_DISK}%${primary_disk}%g" "${script_destination_path}"
	sed -i "s%\${VM_MEM_SIZE_MB}%${memory_mb}%g" "${script_destination_path}"
}


# Source the common build setup script, so that we're pyrex-enabled and our
# working directory is changed to the build directory.
. "${SCRIPT_ROOT}/build.common.sh"

# Realize filepaths which might be relative to the OE build workspace
DEFAULT_IMAGES_DIR=$(realpath "${DEFAULT_IMAGES_DIR}")
build_workspace=$(realpath "$build_workspace")

# clean the vm workspace
log INFO "Using workspace: $build_workspace"
rm -Rf "$build_workspace"
[ ! -e "$build_workspace" ]
mkdir -p "$build_workspace"
pushd "$build_workspace" >/dev/null

create_answers_iso

# Check that the recovery ISO path is valid.
# We are doing this late in the script because the path might be relative to
# the OE build workspace, and we have just recently changed into it.
recovery_iso=$(realpath "${recovery_iso:=${DEFAULT_IMAGES_DIR}/${RECOVERY_IMAGE_RECIPE_NAME}-x64.iso}")
if [ ! -r "${recovery_iso}" ]; then
	log ERROR "Recovery ISO at ${recovery_iso} does not exist or is not readable."
	exit 2
fi

vm_fullname=${vm_name}-x64

build_qemu_vm "${vm_fullname}" "./${vm_fullname}-qemu"

archive_vm_dir "${vm_fullname}-qemu"

popd >/dev/null
exit 0
