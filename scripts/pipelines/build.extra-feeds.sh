#!/bin/bash
set -euo pipefail

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))
DELETE_DUPLICATE_IPKS="bash ${SCRIPT_ROOT}/delete-duplicate-ipks.sh"

## ARGUMENT PARSING
usage() {
	cat <<EOF
$(basename $BASH_SOURCE) [CORE_FEED_PATH]
Builds the NILRT extra/ package feed. If CORE_FEED_PATH is asserted, also
remove any packages from the extras feed which is already in core/.

Positionals:
CORE_FEED_PATH  Filepath to the root of the NILRT core/ IPK feed.
EOF
	exit ${1:-2}
}

positionals=()
while [ $# -ge 1 ]; do case "$1" in
	-h|--help)
		usage 0
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
core_feed_path="$(realpath ${positionals[0]})"


## MAIN
. "${SCRIPT_ROOT}/build.common.sh" >/dev/null
# Now in the OE+Pyrex build/ workspace...

echo "INFO: Building the extra package feed."
set -x
bitbake packagegroup-ni-desirable
#bitbake --continue packagegroup-ni-extra
set +x

# If the user provided a core/ feed path, dedupe against it.
if [ -n "${core_feed_path}" ]; then
	[ -d "$core_feed_path" ] || (echo "ERROR: core feed path $core_feed_path is not a directory." >&2; exit 1)

	echo "Pruning all packages from the extras feed which are already in core."
	$DELETE_DUPLICATE_IPKS \
		"${core_feed_path}" \
		"./tmp-glibc/deploy/ipk"
fi

# Package index generation must happen after we have deduped IPKs.
echo "INFO: Generating extra/ feed indexes."
bitbake package-index
