#!/bin/bash
set -euo pipefail

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))
DELETE_DUPLICATE_IPKS="bash ${SCRIPT_ROOT}/delete-duplicate-ipks.sh"

## ARGUMENT PARSING
usage() {
	cat <<EOF
$(basename $BASH_SOURCE) [--help] [--desirable-only] [--no-index] \\
    [CORE_FEED_PATH]

Builds the NILRT extra/ package feed. If CORE_FEED_PATH is asserted, also
remove any packages from the extras feed which is already in core/.

# Options
-d, --desirable-only
  If asserted, only build the 'desirable' packagegroup and do not attempt to
  build the entire 'extra' feed (which takes a long time.)
-n, --no-index
  If asserted, skip creating the package-index at the end of feed generation.

# Positional Arguments
CORE_FEED_PATH
  Filepath to the root of the NILRT core/ IPK feed.
EOF
	exit ${1:-2}
}

desirable_only=false
skip_package_index=false
core_feed_path=""

positionals=()
while [ $# -ge 1 ]; do case "$1" in
	-h|--help)
		usage 0
		;;
	-d|--desirable-only)
		desirable_only=true
		shift
		;;
	-n|--no-index)
		skip_package_index=true
		shift
		;;
	-*|--*)
		echo "ERROR: unknown option: $1" >&2
		usage >&2
		;;
	*)
		positionals+=($1)
		shift
		;;
esac; done
# Assign positionals to named variables, because scripts that we source later
# in this file (eg. ni-oe-init-build-env) can overwrite the "positionals"
# variable as a part of their native arg-parsing.
# core_feed_path must be absolute here, because entering the pyrex build env
# will switch the CWD.
if [ ${#positionals[@]} -gt 0 ]; then
	core_feed_path="$(realpath ${positionals[0]})"
fi


## MAIN
. "${SCRIPT_ROOT}/build.common.sh" >/dev/null
# Now in the OE+Pyrex build/ workspace...

echo "INFO: Building the extra package feed."
bitbake packagegroup-ni-desirable

if [ ! "$desirable_only" = true ]; then
	bitbake --continue packagegroup-ni-extra || true
else
	echo "INFO: 'desirable-only' requested; skipping full extra feed build."
fi

# If the user provided a core/ feed path, dedupe against it.
if [ -n "${core_feed_path}" ]; then
	[ -d "$core_feed_path" ] || (echo "ERROR: core feed path $core_feed_path is not a directory." >&2; exit 1)

	echo "Pruning all packages from the extras feed which are already in core."
	$DELETE_DUPLICATE_IPKS \
		"${core_feed_path}" \
		"./tmp-glibc/deploy/ipk"
fi

# Package index generation must happen after we have deduped IPKs.
if [ "$skip_package_index" != true ]; then
	echo "INFO: Generating extra/ feed indexes."
	bitbake package-index
else
	echo "INFO: Skipping package index generation by user request."
fi
