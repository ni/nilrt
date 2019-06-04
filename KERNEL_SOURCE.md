# ﻿NI Linux Real-Time Kernel Source README

## Introduction

Use these instructions to build a kernel that can boot on NI Linux Real-Time
targets.

**Note:** National Instruments does not support kernels other than one provided by
National Instruments. Any kernel other than what is provided by National
Instruments may not have the same performance, determinism, features, or basic
functionality.


## Requirements

* A Linux machine to build the kernel
* GNU ``make``
* The ``mksquashfs`` utility
* The distribution-dependent packages required to build the Linux kernel source
* (ARM Only) The ``u-boot-tools`` package


## Downloading the Kernel Source

The kernel source for both Intel x86-based and ARM-based NI Linux  Real-Time
targets is available for download on NI's GitHub repository. Clone it using the
``git`` source control tool.

```bash
git clone https://github.com/ni/linux.git linux
```

Checkout the git branch corresponding to the release you wish to use. The
example below corresponds to the 2015 release.

```bash
cd linux
# git checkout $git_branch
git checkout nilrt_pub/15.0/3.14
```


## Using the Tools
You can use any cross-compilation toolchain of your choosing, or you can
download the toolchains [from
ni.com](https://search.ni.com/nisearch/app/main/p/bot/no/ap/global/lang/en/pg/1/q/GNU%20C%20&%20C++%20Compiler/)
or build them yourself.


### Building the Toolchain Yourself

Refer to the ``README.md`` in this repo to get started with building
OpenEmbedded components. Configure your environment and build the
``meta-toolchain`` component.

```bash
    source env-$DISTRO-$MACHINE
    bitbake meta-toolchain
```

This creates the tools you need to build the kernel. Extract the toolchain IPK
to a location on your computer, optionally placing the tools on your ``$PATH``
environment variable.


## Compiling the kernel

Set the kernel configuration to match NI’s settings:

```bash
# ARMV7-A:
export ARCH=arm
export CROSS_COMPILE="${toolchain_path}/bin/arm-nilrt-linux-gnueabi-"
make nati_zynq_defconfig

# X86_64:
export ARCH=x86_64
export CROSS_COMPILE="${toolchain_path}/x86_64-nilrt-linux-"
make nati_x86_64_defconfig

# ex. CROSS_COMPILE
# export CROSS_COMPILE=${HOME}/sysroots/x86_64-nilrtsdk-linux/usr/bin/armv7a-vfp-neon-nilrt-linux-gnueabi/arm-nilrt-linux-gnueabi-
```

If you are using the 2017 or later toolchain, you also must export the following
variable

```bash
export TGT_EXTRACFLAGS="--sysroot=/path/to/target/sysroot"
# ex.
# export TGT_EXTRACFLAGS="--sysroot=${HOME}/sysroots/cortexa9-vfpv3-nilrt-linux-gnueabi/"
```

Once all of the above environment variables are set in your shell, you can
create the kernel image, headers squashfs image, and modules using ``make``.

```bash
make ni-pkg
```

Now copy the kernel image, modules, and header squashfs to the target. It is
recommended that you use the Secure Shell Server (SSH) or enable WebDAV and use
it to transfer the files.

In all of the following, ``KERNEL_ROOT`` refers to the location where the kernel
source exists on your Linux build machine. ``ARCH`` refers to the processor
architecture for which you built the kernel. ``rt_target_hostname`` refers to
the hostname (or IP) of the RT target to which you're deploying.

```bash
# Copy the kernel to the target #
# ARM only
scp ${KERNEL_ROOT}/ni-install/arm/boot/ni_zynq_custom_runmodekernel.itb \
    admin@${rt_target_hostname}:/boot/linux_runmode.itb

# x86_64 only
scp ${KERNEL_ROOT}/ni-install/x86/boot/bzImage \
    admin@${rt_target_hostname}:/boot/runmode/


# Copy kernel modules
scp -r ${KERNEL_ROOT}/ni-install/${ARCH}/lib/modules/ \
       admin@${rt_target_hostname}:/lib/modules/${VERSION}/
# Note that the newly-built modules directory contains symbolic links to the
# build and source directories; do not copy the linked directories to your
# target.

# Copy headers squashfs
scp ${KERNEL_ROOT}/ni-install/${ARCH}/headers/headers.squashfs \
    admin@${rt_target_hostname}:/usr/local/natinst/tools/module-versioning-image.squashfs

# Remove the cached version of the kernel header
ssh admin@${rt_target_hostname} "rm -vf /usr/local/natinst/tools/module-versioning-image.squashfs"
```

Reboot the target and check that the target successfully boots. Log into a shell
and check that your kernel is running by issuing ``uname -a``.

At this point, the NI drivers need to be updated to work with the new kernel.

```bash
source /usr/local/natinst/tools/versioning_utils.sh
setup_versioning_env
versioning_call /usr/local/natinst/nikal/bin/updateNIDrivers $(kernel_version)
```

After successfully running these commands, reboot the target.

----

## HELP! MY TARGET DOESN'T BOOT!

If, after building and putting a new kernel on the target, you are unable
to boot successfully, refer to your controller's documentation on forcing
the controller to boot into safe mode and reformat using MAX.

----

**NOTE:** Changes to the kernel running on the target will be lost in certain
operations from MAX, including formatting the target and uninstalling all
components.
