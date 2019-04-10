FROM debian:9.8

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN sed -i 's/stretch main/stretch main contrib/' /etc/apt/sources.list

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --assume-yes apt-utils

# Install OE dependencies
RUN apt-get update && apt-get install --assume-yes \
	bc \
	build-essential \
	ccache \
	chrpath \
	cpio \
	cvs \
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
	libguestfs0-dbg \
	libguestfs-tools \
	libpulse-dev \
	libsdl1.2-dev \
	linux-image-amd64 \
	locales \
	pigz \
	pkg-config \
	python \
	python-pexpect \
	python3 \
	qemu-kvm \
	qemu-system-x86 \
	qemu-utils \
	rsync \
	socat \
	strace \
	subversion \
	sudo \
	texi2html \
	texinfo \
	unzip \
	uuid-runtime \
	vim \
	wget \
	xmlstarlet \
	zip

# Install virtualbox from upstream because it's not available in debian 9
RUN echo 'deb http://download.virtualbox.org/virtualbox/debian stretch contrib' > /etc/apt/sources.list.d/virtualbox.list
RUN wget https://www.virtualbox.org/download/oracle_vbox_2016.asc
RUN apt-key add oracle_vbox_2016.asc
RUN rm oracle_vbox_2016.asc
RUN apt-get update && apt-get install --assume-yes virtualbox-6.0

RUN dpkg-reconfigure -f noninteractive locales
RUN echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen && locale-gen en_US.UTF-8
RUN update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

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

ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'
