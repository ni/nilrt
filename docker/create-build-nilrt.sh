#!/bin/bash
set -u

SCRIPT_ROOT=$(realpath $(dirname ${BASH_SOURCE}))
PYREX_ROOT=$(realpath "${SCRIPT_ROOT}/../sources/pyrex")
PYREX_BASE=ubuntu-18.04-oe

IMAGE_NAME=build-nilrt

usage() {
	cat >&2 <<EOF
$(basename) [-c TAG_CODENAME] [TAG_BRANCH]
Creates a new build-nilrt container based on the garmin/pyrex containers, and
tags it with the current nilrt.git repo shorthash, as 'latest', and
(optionally) with the current OE branch name.

Arguments:
-c, --codename  The codename (e.g. 'hardknott') of the meta-nilrt.git repo. If
                not set, the codename will be parsed from meta-nilrt's
                layer.conf.

Positionals:
TAG_BRANCH  The 'branch' name of the current nilrt.git repo (eg. 'dunfell'). If
            not set, the docker container will not be tagged with the branch
            name.
EOF
	exit ${1:-2}
}

tag_codename=""
positionals=()
while [ $# -ge 1 ]; do case "$1" in
	-h|--help)
		usage 0
		;;
        -c|--codename)
            shift
            if [ $# -lt 1 -o ! -z "$tag_codename" ]; then
                usage
            fi
            tag_codename="$1"
            shift
            ;;
	*)
		positionals+=($1)
		shift
		;;
esac
done

set -x

# consume positionals
tag_branch=${positionals[0]:-}


# parse out the short git hash, to tag this image with the current commit
pushd "${SCRIPT_ROOT}"
short_hash=$(git rev-parse --short HEAD)
popd

# optionally parse the NIRLT codename from the meta-nilrt:layer.conf
if [ -z "${tag_codename}" ]; then
	NILRT_codename=$(grep -e '^LAYERSERIES_COMPAT_meta-nilrt' "${SCRIPT_ROOT}/../sources/meta-nilrt/conf/layer.conf" | cut -d'"' -f2)
	if [ -z "$NILRT_codename" ]; then
		echo "ERROR: could not parse NILRT_codename from the meta-nilrt layer." >&2
		exit 1
	else
		echo "INFO: using NILRT_codename=${NILRT_codename}"
	fi
fi


set -e
# build the pyrex base image
docker build \
	-f "${PYREX_ROOT}/image/Dockerfile" \
	-t "pyrex-base:${NILRT_codename}" \
	--build-arg=PYREX_BASE=$PYREX_BASE \
	"${PYREX_ROOT}/image"

# build the build-nilrt image
docker build \
	-f "${SCRIPT_ROOT}/build-nilrt.Dockerfile" \
	-t "${IMAGE_NAME}:${short_hash}" \
	--build-arg=PYREX_IMAGE=pyrex-base:${NILRT_codename} \
	"${SCRIPT_ROOT}"

# tag the image with the NILRT codename
docker tag \
	"${IMAGE_NAME}:${short_hash}" \
	"${IMAGE_NAME}:${NILRT_codename}"

# optionally tag it with the branch name
if [ -n "${tag_branch}" ]; then
	docker tag \
		"${IMAGE_NAME}:${short_hash}" \
		"${IMAGE_NAME}:${tag_branch}"
fi
set +e
