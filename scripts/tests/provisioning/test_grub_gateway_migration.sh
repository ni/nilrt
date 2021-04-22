#!/bin/bash
#
# This script should be run to verify the functionality of the
# dist-nilrt-grub-gateway IPK.
# This test:
#  * boots an already-provisioned NILRT QEMU virtual machine, using the RAUC
#    (efi-ab) bootflow.
#  * configures opkg with a locally-hosted ipk feed
#  * installs and run the dist-nilrt-grub-gateway IPK, to reprovision the VM as
#    a legacy safemode (grub) image
#  * reconfigures opkg with the locally-build dist/ feed
#  * installs and runs the grub-gateway ptest suite
#
#  This script returns 0 when the grub-gateway ptest suite passes, or a
#  positive value otherwise.
set -euo pipefail

SCRIPT_ROOT=$(dirname "$BASH_SOURCE")

usage () {
	cat <<EOF
$(basename $0) nilrt_vm_directory dist_feed_path other_ipk_feeds
	       [other_ipk_feeds...]
EOF
	exit ${1:-2}
}

if [ $# -lt 3 ]; then
	echo "ERROR: invalid or missing arguments." >&2
	usage
fi

vm_dir=${1}
dist_feed=${2}
ipk_feeds=(${@:3})
log_file=./$(basename ${BASH_SOURCE%.*}).log

(
	bash "${SCRIPT_ROOT}/start-vm-using-expect.sh" \
		${ipk_feeds[@]/#/--ipk-feed /} \
		--ipk-feed "${dist_feed}" \
		"${vm_dir}" \
		migrate_vm_to_safemode.expect

	bash "${SCRIPT_ROOT}/start-vm-using-expect.sh" \
		--ipk-feed "${dist_feed}" \
		"${vm_dir}" \
		test_safemode_provision.expect
) | tee $log_file

# Quickly parse the test session log for pass/fail status
# GREP will return code...
#   0, if the ptest PASS line is present
#   1, if the line is not present (or is FAIL: or SKIP:)
#   2, if the log file does not exist for whatever reason
echo "INFO: Parsing the test log..."
if grep -E '^PASS: ni_provisioning\W' ./${log_file}; then
	echo "INFO: grub migration test passes."
	exit 0
else
	echo "INFO: grub migration test failed."
	exit 1
fi
