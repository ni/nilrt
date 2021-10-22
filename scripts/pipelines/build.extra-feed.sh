#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh"

echo "INFO: Building the extra package feed."
bitbake packagegroup-ni-desirable
bitbake --continue packagegroup-ni-extra
bitbake package-index
