#!/bin/bash

SCRIPT_ROOT=$(realpath $(dirname $BASH_SOURCE))

. "${SCRIPT_ROOT}/build.common.sh" "$@"

echo "INFO: Setting SDKMACHINE to x86_64-mingw32"
export SDKMACHINE="x86_64-mingw32"
export SDK_ARCHIVE_TYPE="zip"

echo "INFO: Building meta-toolchain"
bitbake meta-toolchain
