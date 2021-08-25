NI Linux Real-Time Distribution
======

Introduction
------

Downloads the NI Linux Real-Time (NILRT) source code and
provides scripts to aid in building images and packages.

Build Steps
------

1. Get the source by running the following commands:
    ```bash
    git clone https://github.com/ni/nilrt.git
    cd nilrt
    git checkout nilrt/$release
    git submodule init
    git submodule update --remote --checkout
    ```

2. Set up your build environment.

    It is highly recommended that you use the included Dockerfile in
    `:scripts/docker/` to create a build container, and use it as your bitbake
    environment. OE builds are highly sensitive to the host toolchain, and you
    may experience odd bitbake errors if your native OS has tools which are
    too-new or too-old.

    Once you've entered your prefered build environment, source the
    initialization script at the project root.

    ```bash
    . nilrt-build-init.env [--org]
    ```

    <font color=lightgreen>[NI]</font> builders who are connected to the NI
    corporate network should specify `--org` in their init script args, to
    provoke the script into adding the `ni-org.conf` snippet to your bitbake
    directory. External builders *should not* use `--org`.

    This will setup the needed environment variables and build configuration
    files for building through the OpenEmbedded build system. Note that the
    configuration files (that exist in the build/conf directory) include some
    basic default configurations, allowing modification or overriding of these
    default configurations.

3. Build the package or packages that you want for your target. For example, to
build the Python3, Ruby, and Apache targets, run the following commands:

    ```bash
    bitbake python3 ruby apache2
    ```

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

4. (Optional/Advanced) Bitbake can transform tmp-glibc/deploy/ipk/ into
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

5. (Optional/Advanced) Build a bootable recovery disk by running the
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

6. (Optional/Advanced) Build a NILRT Software Development Kit (SDK) with
GCC compiler toolchain.

    Run the following to build an SDK for x64 Linux machines:

        SDKMACHINE=x86_64 bitbake -c populate_sdk host-toolchain-sysroot

    Run the following to build an SDK for x86 Windows machines:

        SDKMACHINE=i686-mingw32 bitbake -c populate_sdk host-toolchain-sysroot

    The resulting archives are located at the following paths for Linux
and Windows, respectively:

        tmp-glibc/deploy/sdk/oecore-x86_64-*.sh
        tmp-glibc/deploy/sdk/oecore-i686-*.tar.bz2

    The Linux archive is a self-extracting shell script (a.k.a. shar).
To install the SDK, copy archive to your build machine and run it with
the following arguments to extract into your $HOME directory:

        /path/to/oecore-x86_64-*.sh -y -d "$HOME/NILRTSDK"

    $HOME/NILRTSDK/sysroots/x86_64-nilrtsdk-linux/ is a *NIX style
system root (sysroot) for your build machine. It contains a GCC
cross-compiler which may run on your build machine to produce NILRT
binaries.

    The other directory under $HOME/NILRTSDK/sysroots/ is an NILRT
system root containing headers and shared libraries that GCC may link
during it's build process. These are the same files you might find on
an NILRT system. The name of this sysroot directory depends on the
configured $MACHINE and tuning options in NILRT config files.

    The Windows archive is a bzipped tarball, which may be extracted by
any compatible archiver utility. It has a similar directory structure as
the Linux shar, but the build system's sysroot is named
i686-nilrtsdk-mingw32 instead of x86_64-nilrtsdk-linux. It will have the
same NILRT sysroot.

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
