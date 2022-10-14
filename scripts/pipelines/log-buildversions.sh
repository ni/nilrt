#!/bin/bash
# This script creates a file documenting the commits
# used to during the most recent build. The file
# includes both the commits used by AUTOREV packages
# and the commits used for the git submodules.

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

function usage() {
    cat <<EOF
$(basename $0) [-h] [-a]

Get information on the specific commit versions for NILRT components after a build.

# Options
-h
    Print this message and exit.
-a
    Include all SRCREVs and not just AUTOREVs.
EOF
}

buildhistory_opts=
while getopts ":ho:a" opt; do
    case $opt in
        h )
            usage >&1
            exit 0
            ;;
        a )
            buildhistory_opts="-a"
            ;;
        \? )
            echo "ERROR: Invalid option -${OPTARG}." >&2
            exit 1
            ;;
    esac
done
shift $(($OPTIND - 1))

# Gets nilrt and submodule repo hashes.
function get_repo_hashes() {
    local nilrt_rev=$(git rev-parse HEAD)
    local submodule_status=$(git submodule status)
    cat <<EOF
# git repo hashes for nilrt and submodules.
# Checkout these commits to use the same versions as this build.
nilrt commit id: $nilrt_rev

# Submodules
$submodule_status
EOF
}

# Gets SRCREV values from the OE buildhistory.
function get_rev_commits() {
    local buildhistory_dir=buildhistory/
    if [ -d buildhistory/ ]; then
        local buildhistory_output="$(buildhistory-collect-srcrevs ${buildhistory_opts})"
        cat <<EOF
# Build revisions used for recipes. Copy into local.conf or a similar
# global conf file to staple to the same revisions used for this build.
$buildhistory_output
EOF
    else
        >&2 echo "ERROR: No buildhistory directory at $buildhistory_dir. Make sure a build with buildhistory enabled occured."
        exit 1
    fi
}

. "${SCRIPT_ROOT}/build.common.sh" > /dev/null

REPO_HASHES="$(get_repo_hashes)"
ACTUALREVS="$(get_rev_commits)"

echo "$REPO_HASHES"
echo
echo "$ACTUALREVS"
