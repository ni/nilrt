ARG PYREX_IMAGE
FROM ${PYREX_IMAGE} as build-nilrt

RUN apt-get update && apt-get install --assume-yes \
	genisoimage \
	qemu-utils \
	qemu-system-x86 \
""

# this Dockerfile layer contains nothing yet.
