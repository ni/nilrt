ARG PYREX_IMAGE=pyrex-oe:latest
FROM ${PYREX_IMAGE} AS build-nilrt

# ISO and QEMU utilities are needed by the build.vm.sh pipeline scriptlet.
RUN apt-get update && apt-get install --assume-yes \
	genisoimage \
	qemu-system-x86 \
	qemu-utils \
	libtinfo6 \
	openssh-client \
""
