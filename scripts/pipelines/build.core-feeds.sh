#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh" $@

echo "INFO: Building the core package feed."
bitbake packagefeed-ni-core
bitbake package-index

# ni-safemode-image wraps a safemode image built from this feed, so it can only
# be built once the feed is complete and indexed.
if [ "$(bitbake-getvar --value --quiet MACHINE)" = "x64" ]; then
	echo "INFO: Adding the safemode image package to the core package feed."
	bitbake ni-safemode-image
	bitbake package-index
fi

# AB#2791248: Build the Linux Kernel to ensure CVEs are made available
bitbake linux-nilrt
