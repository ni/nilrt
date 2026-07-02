#!/usr/bin/env bash

set -euo pipefail

: "${TOOLS_DIR:?TOOLS_DIR environment variable is not set}"

required_cmds=(jq curl tar sha256sum perl mktemp grep realpath)
for cmd in "${required_cmds[@]}"; do
    if ! command -v "$cmd" >/dev/null; then
        echo "Required command '$cmd' is missing on the agent." >&2
        exit 1
    fi
done

# TOOLS_DIR is provided by the caller because the installed binaries must live
# at a stable path that later, independent pipeline steps add to PATH. Resolve
# it to an absolute path so the later `cd` into the scratch dir cannot break the
# copy targets, then create it. Tools are written with fixed names and overwrite
# in place, so there is no need to wipe the directory first.
TOOLS_DIR="$(realpath -m -- "$TOOLS_DIR")"
mkdir -p -- "$TOOLS_DIR"

export PATH="$TOOLS_DIR:$PATH"

echo "Installing git-send-email..."

GIT_SEND_EMAIL_SHA256=15094e3fc8cfbe7931a9aceac99bdc82537d42d3be67ee90518b2371fc7869bf

curl \
    --fail \
    --location \
    --show-error \
    --connect-timeout 30 \
    --max-time 300 \
    https://raw.githubusercontent.com/git/git/v2.44.0/git-send-email.perl \
    -o "$TOOLS_DIR/git-send-email"

echo "${GIT_SEND_EMAIL_SHA256}  ${TOOLS_DIR}/git-send-email" \
    | sha256sum -c -

chmod +x "$TOOLS_DIR/git-send-email"

echo "Installing GitHub CLI..."

readonly GH_VERSION="2.47.0"
readonly GH_ARCH=amd64

workdir="$(mktemp -d)"
cleanup() {
    rm -rf -- "$workdir"
}
trap cleanup EXIT

cd -- "$workdir"

curl \
    --fail \
    --location \
    --show-error \
    --connect-timeout 30 \
    --max-time 300 \
    -o "gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz" \
    "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"

curl \
    --fail \
    --location \
    --show-error \
    --connect-timeout 30 \
    --max-time 300 \
    -o checksums.txt \
    "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_checksums.txt"

grep -F "gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz" checksums.txt \
    | sha256sum -c -

tar -xzf "gh_${GH_VERSION}_linux_${GH_ARCH}.tar.gz"

cp \
    "gh_${GH_VERSION}_linux_${GH_ARCH}/bin/gh" \
    "$TOOLS_DIR/gh"

chmod +x "$TOOLS_DIR/gh"

command -v git-send-email >/dev/null
command -v gh >/dev/null

gh --version

echo "All required tools are ready."
