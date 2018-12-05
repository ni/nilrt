#!/bin/bash
set -e -o pipefail

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

NIBUILD_PACKAGE_INDEX_SIGNING_URL="$1"
NIBUILD_PACKAGE_INDEX_SIGNING_KEY="$2"
COMMENT_PREFIX="$3"

# check env
[ -n "$MACHINE" ] || error_and_die 'No MACHINE specified in env'
bitbake --parse-only >/dev/null || error_and_die 'Bitbake failed. Check your environment. This script must be run from the build directory.'

for filepath in `find ./tmp-glibc/deploy/ipk/ -name Packages -o -name Packages.gz`; do
    echo "Signing $filepath"

    rm -f "$filepath.asc"

    ssh -oBatchMode=yes "$NIBUILD_PACKAGE_INDEX_SIGNING_URL" -- \
        --key "$NIBUILD_PACKAGE_INDEX_SIGNING_KEY" \
        --comment "\"$COMMENT_PREFIX $filepath\"" \
        sign <"$filepath" >"$filepath.asc"

    ls "$filepath.asc" >/dev/null

    echo "Done"
done
