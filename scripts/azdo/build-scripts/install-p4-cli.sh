#!/usr/bin/env bash
# This script installs the p4 CLI utility on linux docker images.
set -xeuo pipefail

p4_release="r19.2"
p4_cli_uri="https://cdist2.perforce.com/perforce/${p4_release}/bin.linux26x86_64/helix-core-server.tgz"
p4_sha_uri="https://cdist2.perforce.com/perforce/${p4_release}/bin.linux26x86_64/SHA256SUMS"

tmp_p4=`mktemp -d`
cd "$tmp_p4"
wget --no-verbose "${p4_cli_uri}"
wget --no-verbose "${p4_sha_uri}"
sha256sum --strict --ignore-missing --check ./SHA256SUMS

tar -xz -f helix-core-server.tgz --to-stdout 'p4' >/usr/bin/p4
chmod 0755 /usr/bin/p4

rm -rv "$tmp_p4"
