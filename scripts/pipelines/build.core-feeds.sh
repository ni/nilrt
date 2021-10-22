#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh"

echo "INFO: Building the core package feed."
bitbake packagegroup-ni-coreimagerepo
bitbake package-index
