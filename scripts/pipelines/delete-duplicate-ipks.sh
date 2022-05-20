#!/usr/bin/env bash
# This script compares the IPK contents of two feed trees and removes any IPKs
# in the subordinate feed which are already present in the superordinate feed.
set -euo pipefail


function usage() {
	local returncode=${1:-2}
	local helptext=$(cat <<EOF
$(basename $0) [-h|--help] [-n|--dry-run] [-v|--verbose] superordinate subordinate

Compares the IPK contents of two feed trees, optionally removing duplicate IPKs
from the subordinate feed.

Opts:
-h|--help     Print this help text and exit (stdout).
-n|--dry-run  Do everything except actually deleting the common IPKs.
-v|--verbose  Enable verbose reporting of which files are going to be deleted
              (stdout).

Positionals:
(super|sub)ordinate   Path to the feed tree root for each feed in comparison.
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
			shift
			;;
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


## SANITY CHECKS ##
# Since this script involves deleting many files, do a couple sanity checks.
# CHECK 1 - Both feed paths are actually directories
test -d "${feed_super}" || (echo "ERROR: ${feed_super} is not a real directory path." && exit 1)
test -d "${feed_sub}" || (echo "ERROR: ${feed_sub} is not a real directory path." && exit 1)
# CHECK 2 - The feeds are not the same. (If they are, then we would delete every IPK.)
if [ "$(realpath ${feed_super})" = "$(realpath ${feed_sub})" ]; then
	echo "ERROR: Supplied feed paths are actually the same directory." && exit 1
fi


# Collect all the IPK paths from each feed
find_exec="-printf %P\n"

ipk_super=$(find ${feed_super} -name '*.ipk' ${find_exec} | sort)
ipk_sub=$(find ${feed_sub} -name '*.ipk' ${find_exec} | sort)


# find entries common to both feeds
common=$(comm -12 <(cat <<<$ipk_super) <(cat <<<$ipk_sub))

# process each entry
count=0
for entry in $common; do
	sub_entry_path="${feed_sub}/${entry}"
	if $opt_dry_run; then
		$opt_verbose && echo "${sub_entry_path}"
	else
		rm $(if $opt_verbose; then echo --verbose; fi) ${sub_entry_path}
	fi
	count=$(($count + 1))
done

echo "Processed $count common entries."
