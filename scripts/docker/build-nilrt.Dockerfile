FROM debian:10.10 AS build-nilrt-base

ENV DEBIAN_FRONTEND=noninteractive

# Make bash the default shell
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
SHELL ["/bin/bash", "-c"]

# Setup apt
RUN sed -i 's/stretch main/stretch main contrib/' /etc/apt/sources.list
RUN apt-get update && apt-get install --assume-yes apt-utils

# Setup locale
RUN apt-get update && apt-get install --assume-yes locales
RUN dpkg-reconfigure -f noninteractive locales
RUN echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen && locale-gen en_US.UTF-8
RUN update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'

# Install OE dependencies
RUN apt-get update && apt-get install --assume-yes \
	build-essential \
	chrpath \
	cpio \
	debianutils \
	diffstat \
	gawk \
	gcc \
	git \
	iputils-ping \
	libegl1-mesa \
	libsdl1.2-dev \
	mesa-common-dev \
	pylint3 \
	python3 \
	python3-git \
	python3-jinja2 \
	python3-pexpect \
	python3-pip \
	python3-subunit \
	socat \
	texinfo \
	unzip \
	wget \
	xterm \
	xz-utils \
""

# Cleanup image of unneeded packages to reduce size
RUN apt-get autoremove --yes && apt-get clean --yes
RUN rm -rf \
	/tmp/* \
	/var/lib/apt/lists/* \
	/var/tmp/*
RUN rm -f \
	/var/cache/apt/*.bin \
	/var/cache/apt/archives/*.deb \
	/var/cache/apt/archives/partial/*.deb

# Install NILRT project dependencies
RUN apt-get update && apt-get install --assume-yes \
	genisoimage \
	qemu-kvm \
	qemu-system-x86 \
	qemu-utils \
""


FROM build-nilrt-base
ARG BUILD_NILRT_SUDO_UID=""

# Install misc dev-tools
RUN apt-get update && apt-get install --assume-yes \
	vim \
""

# Enable sudo
RUN apt-get update && apt-get install --assume-yes \
	ccache \
	sudo \
	strace \ 
""
RUN if [ -n "${BUILD_NILRT_SUDO_UID}" ]; then \
	echo "#${BUILD_NILRT_SUDO_UID}	ALL=(ALL) NOPASSWD:ALL" >>/etc/sudoers; \
fi
