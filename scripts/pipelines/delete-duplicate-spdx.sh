#!/usr/bin/env bas
# This script compares the SPDX contents of two feeds trees and removes any SPDXs
# in the suboordinate feed which are already present in the superordinate feed.
set -euo pipefail


function usage() {
	local returncode=${1:-2}
	local helptext=$(cat <<EOF
$(basename $0) [-h|--help] [-n|--dry-run] [-v|--verbose] superordinate subordinate

Compares the SPDX contents of two feed trees, optionally removing duplicate SPDXs
from the subordinate feed.

Opts:
-h|--help     Print this help test and exit (stdout).
-n|--dry-run  Do everything except actually deleting the common SPDXs.
-v|--verbose  Enable verbose reporting of which files are going to be deleted
			  (stdout).

Positionals:
(super|sub)oridinate   Path to the feed tree root for each feed in comparison.
EOF
)

	if [ "$returncode" == 2 ]; then
		echo "${helptext}" >&1
	else
		echo "${helptext}" >&2
	fi
	exit $returncode
}

[ $# -lt 1 ] && usage

## OPTIONS PARSING ##
opt_dry_run=false
opt_verbose=false

opt_pos=()
while [ $# -gt 0 ]; do
	case "$1" in
		-h|--help)
			usage 0
			shift
			;;
		-n|--dry-run)
			opt_dry_run=true
			shift
			;;
		-v|--verbose)
			opt_verbose=true
			shift
			;;
		-*)
			usage 2
			;;
		*)
			opt_pos+=("$1")
			shift;;
	esac
done
if [ "${#opt_pos[@]}" -ne 2 ]; then
	usage 2
fi
feed_super=${opt_pos[0]}
feed_sub=${opt_pos[1]}

echo "Comparing feeds:"
echo "Superordinate: ${feed_super}"
echo "Subordinate:   ${feed_sub}"
$opt_dry_run && echo "!! DRY RUN !! No files will be removed."

if [ "${MACHINE}" = "x64" ]; then
	tune="core2-64"
else
	tune="cortexa9-vfpv3"
fi

folder_list="all ${MACHINE} ${tune} x86_64"

for folder in ${folder_list}; do
	## SANITY CHECKS ##
	# Since this script involves deleting many files, do a couple sanity checks.
	# CHECK 1 - Both feed paths are actually directories
	test -d "${feed_super}/${folder}" || (echo "ERROR: ${feed_super}/${folder} is not a real directory path." && exit 1)
	test -d "${feed_sub}/${folder}" || (echo "ERROR: ${feed_sub}/${folder} is not a real directory path." && exit 1)
	# CHECK 2 - The feeds are not the same. (If they are, then we would delete every SPDX.)
	if [ "$(realpath ${feed_super}/${folder})" = "$(realpath ${feed_sub}/${folder})" ]; then
		echo "ERROR: Supplied feed paths are actually the same directory." && exit 1
	fi
done


count=0
for folder in ${folder_list}; do
	# Collect all the SPDX paths from each feed
	find_exec="-printf %P\n"

	spdx_super=$(find ${feed_super}/${folder} -name '*.spdx.json' ${find_exec} | sort)
	spdx_sub=$(find ${feed_sub}/${folder} -name '*.spdx.json' ${find_exec} | sort)


	# find entries common to both feeds
	common=$(comm -12 <(cat <<<$spdx_super) <(cat <<<$spdx_sub))

	# process each entry
	for entry in $common; do
		sub_entry_path="${feed_sub}/${folder}/${entry}"
		if $opt_dry_run; then
			$opt_verbose && echo "${sub_entry_path}"
		else
			rm $(if $opt_verbose; then echo --verbose; fi) ${sub_entry_path}
		fi
		count=$(($count + 1))
	done
done

echo "Processed $count common entries."
