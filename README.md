NI Linux Real-Time Distribution
======

Introduction
------

Downloads the NI Linux Real-Time (NILRT) source code and
provides scripts to aid in building images and packages.

Build Steps
------

1. Get the source by running the following commands:

        git clone https://github.com/ni/nilrt.git
        cd nilrt
        git checkout nilrt/<release>
        git submodule init
        git submodule update --remote --checkout

2. Install docker

    Install the docker engine on your build host. If you can
successfully run docker run hello-world, then you have everything
you should need.

3. Set up pyrex

    Build (or pull) the build-nilrt pyrex container image.

        bash ./docker/create-build-nilrt.sh  # will tag the image as build-nilrt:${NILRT_codename}

        # Verification
        docker images build-nilrt  # should print the image you just built```

4. Set up build environment

    Enter the NILRT build environment. Sourcing the init script the
first time will automatically setup your pyrex container shim. NI
builders who are connected to the NI corporate network should specify
-org in their init script args, to provoke the script into adding the
ni-org.conf snippet to your bitbake directory. External builders
should not use --org.

        . ./ni-oe-init-build-env [--org]

        # Verification
        bitbake --version  # If this succeeds, you're done.```

    This will setup the needed environment variables and build
configuration files for building through OpenEmbedded build system.
Note that the configuration files (that exist in the build/conf
directory) include some basic default configurations, allowing
modification or overriding of these default configurations.

    Set an appropriate MACHINE variable so that bitbake can tune builds
of NILRT for your hardware.

    Run the following command to configure for ARM targets:

        export MACHINE=xilinx-zynq

    or the following command to configure for x64 targets:

        export MACHINE=x64

    **NOTE** It's not recommended to run bitbake for different
MACHINE's in the same workspace (build directory).

5. Build the package or packages that you want for your target.
For example, to build Python, Ruby, and Apache for Zynq targets, run the
following commands:

        bitbake python ruby apache2

    To build every package in National Instruments' feed, run the
following commands:

        bitbake packagegroup-ni-coreimagerepo
        bitbake --continue packagegroup-ni-extra

    **NOTE** The configuration files (build/conf/*.conf) can optionally
be changed to reflect the desired build settings instead of setting
environment variables.

    **NOTE** Building packages through OpenEmbedded can use significant
disk space, on the order of tens of gigabytes. If you are preparing a
virtual machine to build images, make sure to allocate sufficient disk
space.

    The resulting ipk files that can be installed through opkg exist at
the following directory:

        tmp-glibc/deploy/ipk/...

6. (Optional/Advanced) Bitbake can transform tmp-glibc/deploy/ipk/ into
a package feed when you run the following command:

        bitbake package-index

    Your build machine can then host the feed by running the following
command:

        (cd tmp-glibc/deploy/ipk/ && python -m SimpleHTTPServer 8080)
        # press ctrl+c to stop hosting

    This creates a temporary HTTP server on port 8080 that is accessible
to other hosts on your local network. You may need to configure your
firewall to permit Python to access port 8080. Otherwise, the server
will only be accessible locally on address localhost:8080.

7. (Optional/Advanced) Build a bootable recovery disk by running the
following commands:

        bitbake restore-mode-image

    **NOTE** You must build everything in packagegroup-ni-coreimagerepo
(step 3) and build a feed (optional step 4) to build images.

    **NOTE** By default, National Instruments software is pulled from
a feed hosted on ni.com. You can redirect to a mirror by setting
IPK_NI_SUBFEED_URI to any URI supported by opkg in your org.conf,
site.conf, or auto.conf.

    The resulting root file system images for the minimal NILRT run-mode
and recovery disk are located at the following paths:

        tmp-glibc/deploy/images/$MACHINE/minimal-nilrt-image-$MACHINE.tar.bz2
        tmp-glibc/deploy/images/$MACHINE/restore-mode-image-$MACHINE.cpio.gz

    The bootable ISO recovery disk, which you can install onto a USB
memory stick or burn to a CD, is located at the following path:

        tmp-glibc/deploy/images/$MACHINE/restore-mode-image-$MACHINE.wic
        (You can rename it to ".iso" if desired)

    Run the following command to install the bootable ISO recovery image
onto a USB memory stick at /dev/disk/by-id/XXX, where XXX is the
appropriate device node for your hardware:

        sudo dd if=tmp-glibc/deploy/images/$MACHINE/restore-mode-image-$MACHINE.wic of=/dev/disk/by-id/XXX bs=1M

    **WARNING** Setting 'of' to the wrong device will permanently
destroy data and potentially leave your system unbootable. *Use at your
own risk!!!*

    Boot your NI Linux Real-Time compatible hardware from the recovery
disk and follow on-screen instructions to perform a factory reset.

Creating a Docker Build Container
-----

This repository includes a Dockerfile which may be used to construct an
ephemeral build container. The container is a debian base, plus the toolchain
and environment necessary to run bitbake.

Example docker build command:

```
docker build --no-cache=yes \
	--file=./scripts/docker/Dockerfile  \
	--tag=<docker image tag> \
	./scripts/docker
```

---

    Enjoy, and happy hacking!
    ni.com/community/
