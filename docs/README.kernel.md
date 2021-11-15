# ﻿NI Linux Real-Time Kernel Source README

## Introduction

Use these instructions to build a kernel that can boot on
x64 and ARM-based NI Linux Real-Time (NILRT) targets.

Note: National Instruments does not support kernels other than one
provided by National Instruments. Any kernel other than what is
provided by National Instruments may not have the same performance,
determinism, features, or basic functionality.


### Requirements

A Linux machine to build the kernel with:
- GNU Make installed
- u-boot-tools package installed (for ARM)


## Downloading the Source

1. Clone the source from github.com/ni/linux.

    git clone https://github.com/ni/linux.git
    cd linux

2. Checkout the branch that corresponds to the release you are using.

    git checkout nilrt/<release>/4.14

Note that only kernel versions 4.14 and below support ARM targets at
this time.


### Using the Tools

You can use any cross-compilation toolchain of your choosing, or you can
download the toolchains from ni.com, or build them yourself.

The toolchains are available for download at:
x86_64: http://www.ni.com/download/labview-real-time-module-2014/4959/en/
armv7-a: http://www.ni.com/download/labview-real-time-module-2014/4957/en/

Refer to the README to get started with building OpenEmbedded
components, and build the NILRT SDK containing a GCC toolchain.

The README describes how to build SDKs for both Linux and Windows
machines. Building the kernel is presently only supported on Linux.


### Compiling and Installing the kernel

For x64-based targets:

1. Set the kernel configuration to match NI’s settings.

    export ARCH=x86_64
    export CROSS_COMPILE=/path/to/toolchain/usr/bin/x86_64-nilrt-linux/x86_64-nilrt-linux-
    make nati_x86_64_defconfig

2. Compile the kernel.

    make -j<number_of_parallel_jobs> bzImage modules
    make modules_install INSTALL_MOD_PATH=<temporary_host_side_modules_location>

3. (optional) Backup /boot/runmode/bzImage on the target.

    cd /boot/runmode/
    mv bzImage bzImage-`uname -r`

4. Copy the new kernel to the target.

    scp arch/x86/boot/bzImage admin@<target>:/boot/runmode/
    cd <temporary_host_side_modules_location>
    tar cz lib | ssh admin@<target> tar xz -C /

Note that the build and source symlinks in the modules directory do
not need to be copied over to the target. The `tar` command above will
not follow the symlinks.

5. Reboot the target.

    reboot

6. (optional) Check version of the updated kernel on the target.

    uname -a

For ARM-based targets:

1. Set the kernel configuration to match NI’s settings.

    export ARCH=arm
    export CROSS_COMPILE=/path/to/toolchain/usr/bin/arm-nilrt-linux-gnueabi/arm-nilrt-linux-gnueabi-
    make nati_zynq_defconfig

2. Compile the kernel.

    make ni-pkg

3. Copy the new kernel to the target.

    scp ni-install/arm/boot/ni_zynq_custom_runmodekernel.itb admin@<target>:/boot/linux_runmode.itb
    cd ni-install/arm/lib/modules/
    tar cz lib | ssh admin@<target> tar xz -C /

Note that the build and source symlinks in the modules directory do
not need to be copied over to the target. The `tar` command above will
not follow the symlinks.

5. Reboot the target.

    reboot

6. (optional) Check version of the updated kernel on the target.

    uname -a

### Rebuilding NI out-of-tree Drivers with DKMS

DKMS needs access to the kernel headers/config/source in order to
re-version out-of-tree NI drivers. You can copy the full kernel
source to the target and create the appropriate symlinks in
/lib/modules. But, this will not work very well on RT targets that
have limited disk space.

An alternative is to network mount the kernel source directory from
the host build machine.

1. Start the sshd daemon on the host.

    sudo systemctl start sshd

2. Install sshfs on the target.

    opkg update
    opkg install sshfs-fuse
    modprobe fuse

3. Mount the kernel source on the target.

    mkdir /usr/src/linux
    sshfs <user>@<host>:<path_to_kernel_source> /usr/src/linux

4. Fix dangling build and source symlinks.

    cd /lib/modules/`uname -r`/
    rm build source
    ln -s /usr/src/linux source
    ln -s source build

5. Prepare the tools needed for dkms.

    cd /lib/modules/`uname -r`/build
    make prepare
    make modules_prepare

Note that you may need to install the bc package on ARM targets.

6. Re-version the NI modules.

    dkms autoinstall

If you get strange gcc errors during this step, ensure that the gcc
version used to build the kernel on the host machine is compatible
with the gcc version on the target. Check the output logs under:
/var/lib/dkms/<ni_module>/<version>/build/make.log.

7. (optional) Check dkms status.

    dkms status

8. Reboot the target.

**HELP! MY TARGET DOESN'T BOOT!**

If, after building and putting a new kernel on the target, you are unable
to boot successfully, refer to your controller's documentation on forcing
the controller to boot into safe mode and format from MAX.

*** NOTE ***
Changes to the kernel running on the target will be lost in certain operations
from MAX, including formatting the target and uninstalling all components.
