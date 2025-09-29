#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname "${BASH_SOURCE[0]}"))

. "${SCRIPT_ROOT}/build.common.sh" $@

echo "INFO: Cleaning the core package feed and the images."

bitbake -c cleanall packagefeed-ni-core
bitbake -c cleanall package-index
bitbake -c cleanall linux-nilrt
bitbake -c cleanall nilrt-safemode-rootfs
bitbake -c cleanall nilrt-base-system-image
bitbake -c cleanall nilrt-recovery-media
