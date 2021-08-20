#!/bin/bash
set -euo pipefail

SCRIPT_ROOT=$(dirname $BASH_SOURCE)
DOCKER_COMPOSE="docker-compose -f ${SCRIPT_ROOT}/build-nilrt.compose.yml"

set -x
uid=$(id -u)
gid=$(id -g)

$DOCKER_COMPOSE build \
	--build-arg BUILD_NILRT_SUDO_UID=${uid} \
	build-nilrt

$DOCKER_COMPOSE run \
	--user=${uid}:${gid} \
	build-nilrt
