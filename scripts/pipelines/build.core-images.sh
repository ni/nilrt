#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh" $@

echo "INFO: Building safemode rootfs "
bitbake nilrt-safemode-rootfs
echo "INFO: Building base system image "
bitbake nilrt-base-system-image
