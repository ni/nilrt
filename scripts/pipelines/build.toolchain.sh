#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh" "$@"

echo "INFO: Building meta-toolchain"
bitbake meta-toolchain
