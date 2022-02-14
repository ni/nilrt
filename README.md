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


## Entering the Bitbake Build Environment

This project uses the [pyrex](https://github.com/garmin/pyrex) tool to transparently provide most of the toolchain requirements needed to run bitbake. However, there are are still a few setup steps.

1. #### Initial repo and submodules
   Checkout the source and initialize the project submodules.
    ```bash
    git clone https://github.com/ni/nilrt.git
    cd nilrt
    git checkout nilrt/$release
    git submodule init
    git submodule update --remote --checkout
    ```

2. #### Install docker
   [Install the docker engine](https://docs.docker.com/engine/install/) on your build host. If you can successfully run `docker run hello-world`, then you have everything you should need.

3. #### Set up pyrex
   Build (or pull) the `build-nilrt` pyrex container image.
    ```bash
    bash ./docker/create-build-nilrt.sh  # will tag the image as build-nilrt:latest

    # Verification
    docker images build-nilrt:latest  # should print the image you just built
    ```

4. #### Set up build environment
   Enter the NILRT build environment. Sourcing the init script the first time will automatically setup your pyrex container shim.
    ```bash
    . ./ni-oe-init-build-env [--org]

    # Verification
    bitbake --version  # If this succeeds, you're done.
    ```

    <font color=lightgreen>[NI]</font> builders who are connected to the NI corporate network should specify `-org` in their init script args, to provoke the script into adding the `ni-org.conf` snippet to your bitbake directory. External builders *should not* use `--org`.

5. #### Build package or packagegroups
   For example, to build Python, Ruby, and Apache for x64 targets, run the following commands:

        bitbake python ruby apache2

    To build all supported OpenEmbedded packages in NI's feed, run the following commands to build these packagegroups:

        bitbake packagefeed-ni-core
        bitbake --continue packagefeed-ni-extra

    **NOTE** If a package within a package group is updated, rebuilding the package group will automatically rebuild that package and all package depending on that package.

    **NOTE** The configuration files (build/conf/*.conf) can optionally be changed to reflect the desired build settings instead of setting environment variables.

    **NOTE** Building packages through OpenEmbedded can use significant disk space, on the order of 100s of gigabytes. If you are preparing a virtual machine to build images, make sure to allocate sufficient disk space.

    The resulting ipk files that can be installed through opkg exist at the following directory:

        tmp-glibc/deploy/ipk/...
        
6. #### Building package feeds
   Bitbake can transform tmp-glibc/deploy/ipk/<tune> into package feeds when you run the following command:

        bitbake package-index

    You must rebuild the package-index before building images or if any package whom the images you are trying to build depends on has been changed and rebuilt.

7. #### Building various images

    **NOTE** You must build packagefeed-ni-core and package_index first to build images.

    * Build a safemode image by running the following command:

            bitbake nilrt-safemode-rootfs

        The resulting root file system images for the NILRT safemode image is located at the following paths:

            tmp-glibc/deploy/images/x64/nilrt-safemode-rootfs-x64.tar.gz
    
        You can install this on target by copying the file over to the target and running the following command:

            tar xf nilrt-safemode-rootfs-x64.tar.gz -C /boot/.safe/
    
    * Build a runmode image by running the following command:

            bitbake nilrt-base-system-image

        The resulting root file system images for the NILRT runmode image is located at the following paths:

            tmp-glibc/deploy/images/x64/nilrt-base-system-image-x64.tar.gz
    
        You can install this on target by copying the file over to the target while the target is in safe mode and running the following commands:

            tar xf nilrt-base-system-image-x64.tar.gz
            tar xf data.tar.gz -C /mnt/userfs && ./postinst

    * Build a bootable recovery media by running the following command:

            bitbake nilrt-recovery-media

        The bootable recovery media, which you can install onto a USB memory stick or burn to a CD, is located at the following path:

            tmp-glibc/deploy/images/x64/nilrt-recovery-media-x64.iso

        Boot your NI Linux Real-Time compatible hardware from the recovery media and follow on-screen instructions to perform a factory reset.

    **NOTE** By default, National Instruments software is pulled from a feed hosted on ni.com. You can redirect to a mirror by setting IPK_NI_SUBFEED_URI to any URI supported by opkg in your org.conf,site.conf, or auto.conf.

---

    Enjoy, and happy hacking!
    ni.com/community/
