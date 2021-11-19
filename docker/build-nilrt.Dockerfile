ARG PYREX_IMAGE
FROM ${PYREX_IMAGE} as build-nilrt

# ISO and QEMU utilities are needed by the build.vm.sh pipeline scriptlet.
RUN apt-get update && apt-get install --assume-yes \
	genisoimage \
	qemu-system-x86 \
	qemu-utils \
""

# this Dockerfile layer contains nothing yet.
