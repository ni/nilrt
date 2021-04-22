#!/bin/bash
#
# This script should be run as part of the NILRT recovery media ISO build
# pipeline to verify that the media has correctly provisioned a blank machine.
# This script:
#  * boots an already-provisioned NILRT QEMU virtual machine.
#  * configures opkg with a locally-hosted ipk feed.
#  * installs and runs the provisioning ISO's ptest package.
#  * evaluates the ptest results.

script_dir="$(dirname "$0")"

usage () {
	cat <<EOF
$(basename $0) nilrt_vm_directory ipk_feeds [ipk_feeds...]
EOF
	exit ${1:-2}
}

if [ $# -lt 2 ]; then
	echo "ERROR: invalid or missing arguments." >&2
	usage
fi

vm_dir=${1}
ipk_feeds=(${@:2})
log_file=./$(basename ${BASH_SOURCE%.*}).log

(
	bash "$script_dir/start-vm-using-expect.sh" \
		${ipk_feeds[@]/#/--ipk-feed /} \
		"${vm_dir}" \
		test_rauc_provision.expect
) | tee $log_file

# Quickly parse the test session log for pass/fail status
# GREP will return code...
#   0, if the ptest PASS line is present
#   1, if the line is not present (or is FAIL: or SKIP:)
#   2, if the log file does not exist for whatever reason
echo "INFO: Parsing the test log..."
if grep -E '^PASS: ni_provisioning\W' ./${log_file}; then
	echo "INFO: provisioning test passes."
	exit 0
else
	echo "INFO: provisioning test failed."
	exit 1
fi
