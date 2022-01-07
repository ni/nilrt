#!/bin/bash
set -euo pipefail


## CONSTANTS
SCRIPT_ROOT=$(realpath $(dirname ${BASH_SOURCE}))
PYBOOTCHARTGUI="python3 ${SCRIPT_ROOT}/../../sources/openembedded-core/scripts/pybootchartgui/pybootchartgui.py"

# Channels which are only printed when verbose
LOG_VERBOSEONLY_CHANNELS=(DEBUG INFO)
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
	BUILDSTATS_DIRECTORY

# TODO: Program Description here

# Options
-h, --help
    Print this usage information and exit.
-v, --verbose
    Print all log channels during execution.

# Positional Arguments
BUILDSTATS_DIRECTORY
    Filepath to the buildstats directory which should be processed.

# Environmentals

# Returns
EOF
}


buildstats_dir=
positionals=()
verbose=false

while [ $# -ge 1 ]; do case "$1" in
	-h|--help)
		usage
		exit 0
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

if [ ${#positionals[@]} -lt 1 ]; then
	log ERROR "Missing required positional arguments.";
	usage
	exit 2
fi
buildstats_dir=${positionals[0]}
log INFO "Processing buildstats directory: $buildstats_dir"


## MAIN
$PYBOOTCHARTGUI -o "${buildstats_dir}/chart_resources" -M -T -m 999999 -f svg "${buildstats_dir}"
