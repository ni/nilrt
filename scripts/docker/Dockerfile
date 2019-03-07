FROM debian:9.8

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN sed -i 's/stretch main/stretch main contrib/' /etc/apt/sources.list

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --assume-yes apt-utils

# Install OE dependencies
RUN apt-get update && apt-get install --assume-yes \
	gawk wget gnupg2 git-core diffstat unzip texinfo cpio iputils-ping \
	gcc-multilib build-essential chrpath socat libsdl1.2-dev python bc zip \
	genisoimage qemu-kvm qemu-system-x86 qemu-utils uuid-runtime \
	python-pexpect pigz xmlstarlet python3 locales vim sudo ccache cvs info \
	help2man subversion texi2html desktop-file-utils rsync libpulse-dev \
	pkg-config libguestfs-tools linux-image-amd64

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
