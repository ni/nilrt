#!/bin/bash
set -e

usage() {
	local exit_code=${1:-2}
	test $exit_code -eq 0 || exec 1>&2

	cat <<EOF

Syntax:
$(basename $BASH_SOURCE) push local_sstate_cache_dir argo_sstate_cache_dir
   Push the local sstate-cache directory contents to the remote argo
   server directory. Note that this script assumes sequential pushes
   to the cache.

$(basename $BASH_SOURCE) pull local_sstate_cache_dir argo_sstate_cache_dir
   Fetch the latest sstate cache from the remote argo cache directory
   and install to the local sstate-cache directory.

$(basename $BASH_SOURCE) -h
   Print this help message and exit

Arguments:
local_sstate_cache_dir      Path to the local sstate cache directory
argo_sstate_cache_dir       Path to the remote argo sstate cache directory

EOF
	exit $exit_code
}

push_cache() {
	if [ ! -d "$local_sstate_cache_dir" -o -z "$(ls -A $local_sstate_cache_dir 2>/dev/null)" ]; then
		echo $local_sstate_cache_dir is missing/empty. Please provide a valid local_sstate_cache_dir name with sstate-cache contents.
		usage
	fi

	mkdir -p "$argo_sstate_cache_dir"
	pushd "$argo_sstate_cache_dir" >/dev/null

	# Copy the contents of the cache to a temp .latest directory
	# before removing the .latest suffix from the name. Create a
	# DONOTUSE file in the .latest directory until the mv operation is
	# complete. The pull operation will not rsync a folder with this
	# file. Implement this extra precaution because the mv may not be
	# atomic on the argo share.

	temp_argo_dir=$(date +"%s").latest
	trap "{ rm -rf $temp_argo_dir; }" EXIT
	mkdir $temp_argo_dir
	touch $temp_argo_dir/DONOTUSE
	echo Pushing sstate cache to argo at $temp_argo_dir
	cp -rL "$local_sstate_cache_dir"/* $temp_argo_dir/
	mv $temp_argo_dir ${temp_argo_dir%.latest}
	trap - EXIT
	rm ${temp_argo_dir%.latest}/DONOTUSE

	# Cap the number of cache directories on the argo server at
	# max_dir_count. Delete older cache directories exceeding the
	# cap.
	max_dir_count=5  # arbitrarily chosen number
	current_dir_count=$(find * -maxdepth 0 -type d 2> /dev/null | wc -l)
	if [ $current_dir_count -gt $max_dir_count ]; then
		dirs=$(ls -d * | head -$(($current_dir_count - $max_dir_count)))
		for dir in ${dirs[@]}; do
			echo Removing old sstate cache directory $dir
			rm -rf $dir
		done
	fi

	popd >/dev/null
}

pull_cache() {
	if [ ! -d "$argo_sstate_cache_dir" ]; then
		echo Cannot find argo sstate cache directory $argo_sstate_cache_dir
		usage
	fi

	mkdir -p "$local_sstate_cache_dir"
	pushd "$argo_sstate_cache_dir" >/dev/null

	# Rsync the latest cache directory, excluding any directory
	# with a .latest suffix from the search.
	latest_cache_dir=$(ls -r -I *.latest | sed -n 1p)
	# Exclude a directory with the DONOTUSE file.
	if [ -e $latest_cache_dir/DONOTUSE ]; then
		latest_cache_dir=$(ls -r -I *.latest | sed -n 2p)
	fi

	echo Copying over the cache contents from $latest_cache_dir. Might take a while...
	rsync -rltxSWh --info=STATS1 "$latest_cache_dir"/ "$local_sstate_cache_dir"/

	popd >/dev/null
}

validate_args() {
	if [ -z $local_sstate_cache_dir ]; then
		echo Missing local_sstate_cache_dir argument.
		usage
	fi
	if [ -z $argo_sstate_cache_dir ]; then
		echo Missing argo_sstate_cache_dir argument.
		usage
	fi
}

local_sstate_cache_dir=$2
argo_sstate_cache_dir=$3
case "$1" in
	push)
		validate_args
		push_cache
	;;
	pull)
		validate_args
		pull_cache
	;;
	--help|-h)
		usage 0
	;;
	*)
		echo Invalid argument
		usage
	;;
esac

