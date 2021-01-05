# NI Linux Real-Time

## Introduction

This project builds packages and images for the NI Linux RT distribution.

NI Linux RT is a
[Real-Time-scheduling](https://rt.wiki.kernel.org/index.php/CONFIG_PREEMPT_RT_Patch)
enabled OS, for use on NI's embedded hardware devices. This project uses the
[OpenEmbedded](http://www.openembedded.org/wiki/Main_Page) framework to build
and package the kernel, software, images, and installation media which compose
NI Linux RT.

Community (non-NI) developers can use this project to build packages for
open-source software projects, which are installable to their existing NI Linux
RT devices - including custom Linux kernels and kernel modules.


## Building Packages

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
    . nilrt-build-init.env
    ```

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

    ```bash
    bitbake packagegroup-ni-base
    bitbake --continue packagegroup-ni-extra
    ```

    **NOTE** The configuration files (build/conf/*.conf) can optionally
be changed to reflect the desired build settings instead of setting
environment variables.

    **NOTE** Building packages through OpenEmbedded can use significant
disk space, on the order of tens of gigabytes. If you are preparing a
virtual machine to build images, make sure to allocate sufficient disk
space.

    The resulting ipk files that can be installed through opkg exist at
the following directory: `:build/tmp-glibc/deploy/ipk`
