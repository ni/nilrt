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

Additional community documentation can be found at https://nilrt-docs.ni.com.


### Mainlines

This project currently has three concurrent development mainlines (sorry). They are, in short:
* `nilrt/master/scarthgap` - the current **x64** dev HEAD
* `nilrt/master/sumo` - the current **arm32** dev HEAD
* `nilrt-academic/master/sumo` - a forked **arm32** HEAD for [FIRST Robotics Competition](https://www.firstinspires.org/robotics/frc)


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

    **Do not use** the Docker Desktop product as your docker installation. Docker Desktop uses virtual machine indirection that will interfere with this project's docker scripting. Other users have [had success](https://github.com/ni/nilrt/issues/249) switching to the bare docker engine instead.

3. #### Set up pyrex
   Build (or pull) the `build-nilrt` pyrex container image.
    ```bash
    bash ./docker/create-build-nilrt.sh  # will tag the image as build-nilrt:${NILRT_codename}

    # Verification
    docker images build-nilrt  # should print the image you just built
    ```

4. #### Set up build environment
   Source the `ni-oe-init-build-env` script, using the `.` (or `source`) command in your shell. This will automatically setup your OpenEmbedded build environment, and the pyrex container shim that will transparently wrap your bitbake commands.
    ```bash
    . ./ni-oe-init-build-env [--org]

    # Verification
    bitbake --version  # If this succeeds, you're done.
    ```

    If you are building on a virtual machine and do not have nested virtualization enabled on the host, you will need to locally remove the `--device /dev/kvm` entry in the args assignment in the top-level pyrex.ini file.

    If you are building on a host with an older version of libseccomp, you may need to add `--security-opt seccomp=unconfined` entry in the args assignment in the top-level pyrex.ini file to work around build errors, as described [here](https://github.com/moby/moby/issues/43595).

    **NI builders** who are connected to the NI corporate network should specify `-org` in their init script args, to provoke the script into adding the `ni-org.conf` snippet to your bitbake directory. External builders *should not* use `--org`.

   If you are building on a `nilrt/master/*` branch ref (rather than a release branch) **and** if you are building outside of the NI corporate network, you will need to set the version of the `ni-main` opkg feed to one which has already been published to `download.ni.com`. Do this by setting the `NILRT_MAIN_FEED_VERSION` bitbake variable to the latest published release. eg.

   ```
   echo 'NILRT_MAIN_FEED_VERSION = "2022Q3"' >> ./conf/local.conf
   ```

5. #### Build package or packagegroups
   For example, to build Python, Ruby, and Apache for x64 targets, run the following commands:

        bitbake python3 ruby apache2

    To build all supported OpenEmbedded packages in NI's feed, run the following commands to build these packagegroups:

        bitbake packagefeed-ni-core

    **NOTE.** If a package within a package group is updated, rebuilding the package group will automatically rebuild that package and all of its dependencies.

    **NOTE.** The configuration files (build/conf/*.conf) can optionally be changed to reflect the desired build settings instead of setting environment variables.

    **NOTE.** Building packages through OpenEmbedded can use significant disk space, on the order of 100s of gigabytes. If you are preparing a virtual machine to build images, make sure to allocate sufficient disk space.

    The resulting ipk files that can be installed through opkg exist at the following directory:

        tmp-glibc/deploy/ipk/...

6. #### Building package feeds
    The NILRT repo has scripting in the [`:scripts/pipelines/`](https://github.com/ni/nilrt/tree/HEAD/scripts/pipelines) directory, which can be used to automate the process of building package feeds. The NI build pipelines use these scripts directly - so they are canonical.

    ```bash
    # after completing the build setup steps above...
    bash ../scripts/pipelines/build.core-feeds.sh
    ```

    These scripts are also a good source for understanding the steps to build a package feed manually. Note that if you are building package feeds *manually*, you must bitbake the special `package-index` target before using the feed.

7. #### Building various images

    **NOTE** You must build packagefeed-ni-core and package-index first to build images.

    * Build a safemode image by running the following command:

            bitbake nilrt-safemode-rootfs

        The resulting root file system images for the NILRT safemode image is located at the following paths:

            tmp-glibc/deploy/images/x64/nilrt-safemode-rootfs-x64.tar.gz

        You can install this on target by copying the file over to the target and running the following command:

            tar xf nilrt-safemode-rootfs-x64.tar.gz -C /boot/.safe/

    * Build a runmode image by running the following command:

            bitbake nilrt-base-system-image

        The resulting root file system images for the NILRT runmode image is located at the following paths:

            tmp-glibc/deploy/images/x64/nilrt-base-system-image-x64.tar

        You can install this on target by copying the file over to the target while the target is in safe mode and running the following commands:

            tar xf nilrt-base-system-image-x64.tar
            tar xf data.tar.gz -C /mnt/userfs && ./postinst

    * Build a bootable recovery media by running the following command:

            bitbake nilrt-recovery-media

        The bootable recovery media, which you can install onto a USB memory stick or burn to a CD, is located at the following path:

            tmp-glibc/deploy/images/x64/nilrt-recovery-media-x64.iso

        Boot your NI Linux Real-Time compatible hardware from the recovery media and follow on-screen instructions to perform a factory reset.

    **NOTE** By default, National Instruments software is pulled from a feed hosted on ni.com. You can redirect to a mirror by setting IPK_NI_SUBFEED_URI to any URI supported by opkg in your org.conf,site.conf, or auto.conf.

8. #### Building the cross-compile toolchain

    In order to compile custom packages for NI Linux Real-Time on a host system, a cross-compile toolchain is necessary. This can be built directly
    from one of the scripts in the [`:scripts/pipelines/`](https://github.com/ni/nilrt/tree/HEAD/scripts/pipelines) directory. By default, it builds for x86_64 Linux hosts.

    ```bash
    bash ../scripts/pipelines/build.toolchain.sh
    ```

    During the build, a script is generated at `$BUILDDIR/tmp-glibc/deploy/sdk`, with a name like `oecore-x86_64-core2-64-toolchain-9.2.sh`. The script is a self-extracting archive, and can be copied to and executed on an appropriate host system to install the toolchain.

    To build the toolchain for an x86_64 Windows host, there is a different script that can be used.
    
    ```bash
    bash ../scripts/pipelines/build.cross-toolchain.sh
    ```

    During the build, an archive is generated at `$BUILDDIR/tmp-glibc/deploy/sdk`, with a name like
    `oecore-x86_64-core2-64-toolchain.tar.xz`. This archive can be extracted on a Windows system to
    to access the toolchain.

---

    Enjoy, and happy hacking!
    ni.com/community/
