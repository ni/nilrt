# ﻿NI Linux Real-Time Kernel Source README

## Introduction

Use these instructions to build a kernel that can boot on NI Linux Real-Time
(NILRT) targets.

Note: National Instruments does not support kernels other than one provided by
National Instruments. Any kernel other than what is provided by National
Instruments may not have the same performance, determinism, features, or basic
functionality.


### Requirements

1. A linux build machine
2. GNU `make`
3. The `mksquashfs` utility


## Downloading the Source

The kernel source for NI Linux Real-Time kernel is available for download from
NI's fork of the linux repo. The repo follows a mainline-branching model with
mainline branch refs like `nilrt/master/${linux_version_base}` and product
release branch refs like `nilrt/${product_version}/${linux_version_base}`.

```bash
git clone https://github.com/ni/linux.git
cd linux
git checkout nilrt/20.6/4.14  # the NI 20.6 release kernel
```


### Using the Tools

You can use any cross-compilation toolchain of your choosing, or you can
download the toolchains from ni.com
([armv7](https://www.ni.com/en-us/support/downloads/software-products/download.gnu-c---c---compile-tools-for-armv7.html#338449),
[x64](https://www.ni.com/en-us/support/downloads/software-products/download.gnu-c---c---compile-tools-x64.html#338443)),
or build them yourself.

Refer to the README to get started with building OpenEmbedded components, and
build the NILRT SDK containing a GCC toolchain.

The README describes how to build SDKs for both Linux and Windows machines.
Building the kernel is presently only supported on Linux.


### Compiling the kernel

1. Set the kernel configuration to match NI’s settings:

    **ARMV7-A:**

    ```bash
    export ARCH=arm
    export CROSS_COMPILE=/path/to/toolchain/usr/bin/arm-nilrt-linux-gnueabi/arm-nilrt-linux-gnueabi-
    make nati_zynq_defconfig
    ```

    **X86_64:**
    ```bash
    export ARCH=x86_64
    export CROSS_COMPILE=/path/to/toolchain/usr/bin/x86_64-nilrt-linux/x86_64-nilrt-linux-
    make nati_x86_64_defconfig
    ```

2. Build the kernel by running `make ni-pkg` (the `ARCH` and `CROSS_COMPILE`
variables have already been set in the previous steps). This creates the kernel
image, headers squashfs image, and modules suitable for use on NI Linux
Real-Time targets.

    Once the kernel image and support files have been created, copy the kernel
image, modules, and header squashfs to the target. Enable the Secure Shell
Server on your target or enable WebDAV to copy the files to the controller. Note
that `$KERNEL_ROOT` refers to the location where the kernel source exists on
your Linux build machine and $ARCH refers to the architecture for which you
built the kernel.

    **ARMV7-A:**

    The kernel image is the `ni_zynq_custom_runmodekernel.itb` file at
    `$KERNEL_ROOT/ni-install/arm/boot`. Copy this file to
    `/boot/linux_runmode.itb` on the target.

    **X86_64:**

    The kernel image is the bzImage file at `$KERNEL_ROOT/ni-install/x86/boot`.
    Copy this file to `/boot/runmode/` on the target.

    **ALL TARGETS:**

    Copy the resulting `$KERNEL_ROOT/ni-install/$ARCH/lib/modules/` directory to
    the target such that all of the new kernel modules exist on the target at
    `/lib/modules/$VERSION/`.

    Copy the resulting `$KERNEL_ROOT/ni-install/$ARCH/headers/headers.squashfs`
    to the target's `/usr/local/natinst/tools/module-versioning-image.squashfs`
    file.

    Finally, remove the cached version of the kernel header version file by
    deleting the `/usr/local/natinst/tools/kernel_version` file (if it exists).

    Reboot the target and check that the target successfully boots. Log into a
    shell and check that your kernel is running by issuing `uname -a`.

    At this point, you should also be able to install NI drivers to the
    controller from MAX.

-----

**HELP! MY TARGET DOESN'T BOOT!**

If, after building and putting a new kernel on the target, you are unable
to boot successfully, refer to your controller's documentation on forcing
the controller to boot into safe mode and format from MAX.

*** NOTE ***
Changes to the kernel running on the target will be lost in certain operations
from MAX, including formatting the target and uninstalling all components.
