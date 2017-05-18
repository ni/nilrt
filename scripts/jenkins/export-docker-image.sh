#!/bin/bash
set -e

source "${NIBUILD_ENV_SCRIPT_PATH}"
mkdir -p "${NIBUILD_COMPONENT_PATH}"
cd "${NIBUILD_COMPONENT_PATH}"
p4 sync ...
source ./setupEnv.sh
submitExport --yes --revert >/dev/null 2>&1 || echo 'No existing export to revert'
buildExport --yes --nodistribution
submitExport --yes --submit
rm -f buildExport*log* submitExport*log*
