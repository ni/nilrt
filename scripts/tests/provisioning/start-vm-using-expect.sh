#!/bin/bash
#
# This script helps with configuring a QEMU VM
# It:
#  * boots an already-provisioned NILRT QEMU virtual machine.
#  * configures opkg with a locally-hosted ipk feed.
#  * runs the provided expect file
set -euo pipefail

readonly SCRIPT_ROOT=$(dirname "$BASH_SOURCE")


## UTILITY FUNCTIONS

error_and_die() {
	echo "ERROR: " $@ >&2
	exit 1
}


## ARGUMENT PARSING AND ENVIRONMENT

usage() {
	local exit_code=${1:-2}
	test $exit_code -eq 0 || exec 1>&2
	cat <<EOF
$(basename $BASH_SOURCE) -h|--help
  Print this usage information and exit.
$(basename $BASH_SOURCE) [-i ipk_feed_dir] nilrt_vm_path
  Start the NILRT VM, setup the feeds  and run the expect file

Options:
-i|--ipk-feed  Path to a local IPK feed, which will be added to the VM's opkg
               configuration.

Arguments:
nilrt_vm_path  Path to an already-provisioned NILRT VM directory. (See the
               buildVM.sh script in the NILRT.git source.)
expect_file    Path to the .expect file
EOF
	exit $exit_code
}

readonly IPK_FEED_PORT=8990
readonly EXPECT=/usr/bin/expect

# Check environment requirements
test -x "$EXPECT" || error_and_die "$EXPECT not found. This script requires the tcl-expect package to instrument test operations."

VERBOSE=${VERBOSE:-}
ipk_feeds=()
positionals=()

while test -n "${1:-}"; do case "$1" in
	-h|--help)
		usage 0
		;;
	-i|--ipk-feed)
		ipk_feeds+=("$2")
		shift
		shift
		;;
	-*|--*)
		echo "Invalid or unrecognized option: $1"
		usage 2
		;;
	*)
		positionals+=("$1")
		shift
		;;
esac; done

if [ ${#positionals} -lt 2 ]; then
	usage 2
fi

nilrt_vm_path=${positionals[0]}
expect_file=${positionals[1]}
log_file="${expect_file%.*}".log

[ -d "${nilrt_vm_path}" ] || error_and_die "NILRT VM path \"$nilrt_vm_path\" does not exist."


## MAIN

pushd "${nilrt_vm_path}"
main_disk=$(find ./ -name '*-x64.qcow2' -print -quit)
test -n "${main_disk}" || (echo "ERROR: found no main disk image (.qcow2)" >&2; exit 1)

feed_server_setup() {
	trap feed_server_teardown EXIT

	feed_server_pubdir=$(mktemp -d --tmpdir test_provisioning.XXXXX)
	feed_server_pid=

	pushd "${feed_server_pubdir}"

	local feed_id=0
	for ipk_feed in ${ipk_feeds[@]}; do
		echo "INFO: Adding feed path: $ipk_feed"
		ln -sf "$ipk_feed" feed.$feed_id
		feed_id=$(($feed_id+1))
	done

	python3 -m http.server $IPK_FEED_PORT &
	feed_server_pid=$!

	popd
}

feed_server_teardown() {
	# terminate the feed server process
	if [ $feed_server_pid ]; then
		kill -s TERM $feed_server_pid
		echo "INFO: Feed server (${feed_server_pid}) terminated."
		feed_server_pid=
	fi

	# teardown the server's link farm
	if [ -d "${feed_server_pubdir}" ]; then
		rm -v ${feed_server_pubdir}/feed.*
		rmdir "${feed_server_pubdir}"
	fi
	feed_server_pubdir=

	trap - EXIT
}


feed_server_setup

#
# Uncomment here if you would like the test framework to pause and wait for
# your command before continuing.
#read -p Continue?

# Find the VM "run" helper script in the machine directory
vm_run_script=$(find ./ -name 'run-*.sh' -exec realpath {} \;)
test -n "${vm_run_script}" || error_and_die "Could not find VM run script in \"${nilrt_vm_path}\""

# Names like: feed.0, feed.1, et c.
ipk_feeds_names=$(find ${feed_server_pubdir} -maxdepth 1 -type l -printf "%f\n")
popd

# Run the expect file. It should record all stdout to the log file in the VM dir.
"${SCRIPT_ROOT}/${expect_file}" \
	${vm_run_script} \
	${log_file} \
	${ipk_feeds_names}

feed_server_teardown
