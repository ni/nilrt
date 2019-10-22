#!/bin/bash
set -eu -o pipefail

error_and_die () {
    echo >&2 "ERROR: $1"
    exit 1
}

NIBUILD_PACKAGE_INDEX_SIGNING_URL="$1"
NIBUILD_PACKAGE_INDEX_SIGNING_KEY="$2"
COMMENT_PREFIX="$3"
FEED_PATH="$4"

for filepath in `find "$FEED_PATH" -name Packages -o -name Packages.gz`; do
    echo "Signing $filepath"

    rm -f "$filepath.asc"

    ssh -oBatchMode=yes "$NIBUILD_PACKAGE_INDEX_SIGNING_URL" -- \
        --key "$NIBUILD_PACKAGE_INDEX_SIGNING_KEY" \
        --comment "\"$COMMENT_PREFIX $filepath\"" \
        sign <"$filepath" >"$filepath.asc"

    ls "$filepath.asc" >/dev/null

    echo "Done"
done
