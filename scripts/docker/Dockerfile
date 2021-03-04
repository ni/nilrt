## LAYER base OS
FROM debian:10.8 as os-base

RUN rm /bin/sh && ln -s /bin/bash /bin/sh
SHELL ["/bin/bash", "-c"]

# Enable contributor package sources
ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i 's/stretch main/stretch main contrib/' /etc/apt/sources.list
RUN apt-get update && apt-get install --assume-yes apt-utils

# Install UTF-8 locales
RUN apt-get update && apt-get install --assume-yes locales
RUN dpkg-reconfigure -f noninteractive locales
RUN echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen && locale-gen en_US.UTF-8
RUN update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'

# Developer tools
RUN apt-get update && apt-get install --assume-yes \
	binutils \
	bvi \
	bzip2 \
	coreutils \
	git \
	python3 \
	rsync \
	strace \
	sudo \
	tree \
	unzip \
	vim \
	wget \
	xz-utils \
	zip \
""

# OpenEmbedded/Bitbake dependencies
RUN apt-get update && apt-get install --assume-yes \
	bc \
	build-essential \
	ccache \
	chrpath \
	cpio \
	cvs \
	debianutils \
	desktop-file-utils \
	diffstat \
	gawk \
	gcc-multilib \
	gdb \
	genisoimage \
	git-core \
	gnupg2 \
	help2man \
	info \
	iputils-ping \
	libc6-dbg \
	libguestfs-tools \
	libpulse-dev \
	libsdl1.2-dev \
	linux-image-amd64 \
	pigz \
	pkg-config \
	pylint3 \
	python \
	python-pexpect \
	python3 \
	python3-git \
	python3-jinja2 \
	python3-pexpect \
	python3-pip \
	qemu-kvm \
	qemu-system-x86 \
	qemu-utils \
	socat \
	strace \
	subversion \
	texi2html \
	texinfo \
	unzip \
	uuid-runtime \
	wget \
	xmlstarlet \
	xterm \
""

# Testing and Utility dependencies
RUN apt-get update && apt-get install --assume-yes \
	expect \
""

# Install virtualbox from upstream because it's not available in debian 10
RUN echo 'deb http://download.virtualbox.org/virtualbox/debian buster contrib' > /etc/apt/sources.list.d/virtualbox.list
RUN wget https://www.virtualbox.org/download/oracle_vbox_2016.asc
RUN apt-key add oracle_vbox_2016.asc
RUN rm oracle_vbox_2016.asc
RUN apt-get update && apt-get install --assume-yes virtualbox-6.0

# Cleanup image of unneeded packages to reduce size
RUN apt-get autoremove --yes && apt-get clean --yes
RUN rm -rf \
	/tmp/* \
	/var/cache/apt/*.bin \
	/var/cache/apt/archives/*.deb \
	/var/cache/apt/archives/partial/*.deb \
	/var/lib/apt/lists/* \
	/var/tmp/* \
""
