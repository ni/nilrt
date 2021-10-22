#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh" $@

echo "INFO: Building test packages..."
bitbake base-files
echo "INFO: Done building test packages..."
