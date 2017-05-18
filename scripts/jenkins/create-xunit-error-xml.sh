#!/bin/bash

set -e

bitbakeLogFile="$1"
xUnitFile="$2"

if [ ! -e "$bitbakeLogFile" ]; then
    echo "ERROR/SANITY CHECK: Input file '$bitbakeLogFile' missing."
    exit 1
fi

rm -f "$xUnitFile"
echo  >"$xUnitFile" '<?xml version="1.0" encoding="UTF-8"?>'
echo >>"$xUnitFile" '<testsuites/>'

xmlstarlet ed --inplace --subnode "/testsuites" -t elem -n "testsuite name=\"bitbake-package-errors\"" "$xUnitFile"

while read -r line; do
    xmlstarlet ed --inplace --subnode "/testsuites/testsuite[@name=\"bitbake-package-errors\"]" -t elem -n "testcase name=\"$line\"" "$xUnitFile"
done < <(grep '^ERROR: ' "$bitbakeLogFile" | grep '\.bb')
