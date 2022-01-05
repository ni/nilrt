#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh"

echo "INFO: Building the core package feed."
bitbake packagefeed-ni-core
bitbake package-index
