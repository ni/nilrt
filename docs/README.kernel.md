# NI Linux Real-Time Kernel Source README

## Introduction

Use these instructions to build a kernel that can boot on
x64 and ARM-based NI Linux Real-Time (NILRT) targets.

Note: National Instruments does not support kernels other than one
provided by National Instruments. Any kernel other than what is
provided by National Instruments may not have the same performance,
determinism, features, or basic functionality.


### Is it necessary to build the kernel?

Some configurations of the kernel are already available via the package
manager. If one is suitable, this is the simplest option to start using
a modified kernel. Some of the kernels available are:

 - The "nohz" kernel: a kernel configured to reduce scheduling ticks
   (configured with `CONFIG_NO_HZ_FULL=y`). This is useful for realtime
   use cases in certain situations; see the [documentation][nohz-doc]
   for a thorough description of the altered behavior and its
   consequences, as well as the NI-provided [README][nohz-readme] that
   is installed with this kernel.  
   The packagegroup to install is `packagegroup-ni-nohz-kernel`.
 - The "debug" kernel: a kernel with debugging information built in.  
   The packagegroup to install is `packagegroup-ni-debug-kernel`.
 - The "next" kernel: a kernel based on a newer upstream version, with a
   version bump.  
   The packagegroup to install is `packagegroup-ni-next-kernel`.

To install any of these kernels, SSH into the target and issue the
appropriate `opkg` commands (replacing `$KERNEL_PACKAGEGROUP` with the
package name given above):

```bash
# Update package lists from repositories
opkg update
# Install the kernel and supporting packages
opkg install $KERNEL_PACKAGEGROUP
```

then reboot the target to start using the new kernel.

[nohz-doc]: <https://www.kernel.org/doc/html/latest/timers/no_hz.html>
[nohz-readme]: <https://github.com/ni/meta-nilrt/blob/HEAD/recipes-kernel/linux/nilrt-nohz/README.nohz>


### Build Host Requirements

A Linux machine to build the kernel with:
- the [`git`](https://git-scm.com/) source control tool.
- the [GNU make](https://www.gnu.org/software/make/) build tool.
- the [GNU Compiler Collection](https://gcc.gnu.org/) (gcc).
- the GNU `bc` tool.
- the [flex](https://github.com/westes/flex) tool.
- the [bison](https://www.gnu.org/software/bison/) parser.
- the `depmod` kernel module tool.
- (ARM only) the u-boot-tools (`mkimage`, `dumpimage`, et c.)
- headers for: `libelf` and `libssl`

On Debian/Ubuntu, you can satisfy the above dependencies like:

```bash
apt-get update && apt-get install -y \
	bc \
	bison \
	flex \
	gcc \
	git \
	kmod \
	libelf-dev \
	libssl-dev \
	make \
	u-boot-tools \
""
```


## Downloading the Source


### Choosing the Branch

NI's linux repository has various branches of the form
`nilrt/$NI_VERSION/$KERNEL_VERSION`, where `$NI_VERSION` is something
like `master` or `23.3`, and `$KERNEL_VERSION` is the major and minor
portions of the upstream kernel version that the branch is based upon.

Note that only kernel versions 4.14 and below support ARM targets at
this time.

The authoritative source for corresponding NI release versions to kernel
versions is in the recipe for the package on the appropriate branch,
such as the one for the [default kernel][default-kernel-recipe].

To see which versions correspond with the current state of a target, run
these commands on the target while it is in runmode:

```bash
cat /etc/os-release
uname -r
```

For example, if these commands produce these outputs:

```
ID=nilrt
NAME="NI Linux Real-Time"
VERSION="9.3 (hardknott)"
VERSION_ID=9.3
PRETTY_NAME="NI Linux Real-Time 9.3 (hardknott)"
DISTRO_CODENAME="hardknott"
BUILD_ID="23.3.0f139-x64"
VERSION_CODENAME="hardknott"
```

```
5.15.96-rt61
```

The corresponding branch in the linux repository would be `nilrt/23.3/5.15`.

[default-kernel-recipe]: <https://github.com/ni/meta-nilrt/blob/HEAD/recipes-kernel/linux/linux-nilrt_git.bb>


### Cloning the Repository

If it will be necessary to perform kernel builds for several versions,
it may be desirable to retrive the full history:

```bash
git clone -b $BRANCH https://github.com/ni/linux.git
cd linux
```

If a full history is unnecessary, the `--depth` argument can be used to
reduce the download size:

```bash
git clone -b $BRANCH --depth 1 https://github.com/ni/linux
cd linux
```


## Using the Tools

You can use any cross-compilation toolchain of your choosing, or you can
download the toolchains from ni.com, or build them yourself.

The toolchains are available for download:
 - x86_64: http://www.ni.com/download/labview-real-time-module-2014/4959/en/
 - armv7-a: http://www.ni.com/download/labview-real-time-module-2014/4957/en/

Refer to the README to get started with building OpenEmbedded
components, and build the NILRT SDK containing a GCC toolchain.

The README describes how to build SDKs for both Linux and Windows
machines. Building the kernel is presently only supported on Linux.


## Compiling and Installing the kernel

### x86_64 Targets

#### Building the kernel

1. Create the configuration for the kernel.

   - Make sure that the appropriate environment variables are defined
     for cross-compilation:

     ```bash
     export ARCH=x86_64
     export CROSS_COMPILE=/path/to/toolchain/usr/bin/x86_64-nilrt-linux/x86_64-nilrt-linux-
     ```

   - Start with a configuration matching NI's settings:

     ```bash
     make nati_x86_64_defconfig
     ```

   - If it is desirable to adjust the kernel configuration (this is
     uncommon), the `menuconfig` target can be used to open a curses
     interface:

     ```bash
     make menuconfig
     ```

     For example, to use this menu to adjust the maximum number of
     serial ports, navigate to `Device Drivers`, then `Character
     devices`, then `Serial drivers`, and configure the `Maximum number
     of 8250/16550 serial ports`.

2. Compile the kernel.

   - Build the kernel and its modules:

     ```bash
     make -j$(nproc) bzImage modules
     ```

     On a 24-thread CPU, this build command completes in about 3
     minutes.

   - It will be necessary later to organize the modules similar to an
     installation. Install them to a temporary directory on the host:

     ```bash
     TEMP_MODULES=./tmp-modules
     make modules_install INSTALL_MOD_PATH=$TEMP_MODULES
     ```

#### Installing the kernel

In this section, these variables will be used:

```bash
TARGET=<the target's hostname or IP address>
KERNEL_VERSION=`make -s kernelrelease`
```

1. On some old runmode images (versions 21.5 and newer do not have this
   issue), the `/boot/runmode/bzImage` path used by the bootloader is
   not a symbolic link, but rather the kernel itself. To avoid
   overwriting the known-good kernel, rename it appropriately by running
   this command on the target:

   ```bash
   test ! -h /boot/runmode/bzImage && mv /boot/runmode/bzImage /boot/runmode/bzImage-`uname -r`
   ```

2. Copy the new kernel to the target with SSH.

   ```bash
   scp arch/x86/boot/bzImage admin@$TARGET:/boot/runmode/bzImage-$KERNEL_VERSION
   ```

   On the target, rewrite the symlink used by the bootloader.

   ```bash
   ln -sf bzImage-$KERNEL_VERSION /boot/runmode/bzImage
   ```

3. Copy the kernel modules to the target.

   ```bash
   tar cz -C $TEMP_MODULES lib | ssh admin@$TARGET tar xz -C /
   ```

   Note that the build and source symlinks in the modules directory do
   not need to be copied over to the target. The `tar` command above
   will not follow the symlinks.

4. If the kernel or modules are not functional, the system may become
   inaccessible over the network. In such cases, it will be useful to
   have a serial connection or a display and keyboard connected to the
   target, so that it can be booted into safemode if problems
   arise. Change the setting so that the bootloader briefly pauses and
   provides an interactive menu to choose whether to boot into safemode:

   ```bash
   fw_setenv bootdelay 5
   ```

5. Reboot the target.

    ```bash
    reboot
    ```

6. (optional) Check version of the updated kernel on the target.

    ```bash
    uname -r
    ```


### ARM32 Targets

1. Set the kernel configuration to match NI’s settings.

    ```bash
    export ARCH=arm
    export CROSS_COMPILE=/path/to/toolchain/usr/bin/arm-nilrt-linux-gnueabi/arm-nilrt-linux-gnueabi-
    make nati_zynq_defconfig
    ```

2. Compile the kernel.

    ```bash
    make ni-pkg
    ```

3. Copy the new kernel to the target.

    ```bash
    scp ni-install/arm/boot/ni_zynq_custom_runmodekernel.itb admin@<target>:/boot/linux_runmode.itb
    cd ni-install/arm/lib/modules/
    tar cz lib | ssh admin@<target> tar xz -C /
    ```

   Note that the build and source symlinks in the modules directory do
not need to be copied over to the target. The `tar` command above will
not follow the symlinks.

5. Reboot the target.

    ```bash
    reboot
    ```

6. (optional) Check version of the updated kernel on the target.

    ```bash
    uname -r
    ```

## Rebuilding NI out-of-tree Drivers with DKMS

### Transferring the Kernel Source to the Target

DKMS needs access to the kernel headers/config/source in order to
re-version out-of-tree NI drivers.

#### With `sshfs`

If the build host is running an SSH daemon (or is able to start one) and
is accessible over the network, the target can mount the build directory
over the network, saving limited disk space resources.

1. Start the sshd daemon on the host.

    ```bash
    sudo systemctl start sshd
    ```

2. Install sshfs on the target.

    ```bash
    opkg update
    opkg install sshfs-fuse
    ```

3. Mount the kernel source on the target.

    ```bash
    mkdir /usr/src/linux
    modprobe fuse
    sshfs <user>@<host>:<path_to_kernel_source> /usr/src/linux
    ```

#### With `scp` and `tar`

If the target has sufficient disk space, the source can be copied to the
target, as was done earlier when copying the modules to the target.

```bash
ssh admin@$TARGET mkdir /usr/src/linux
tar cz --exclude=./.git --exclude=$TEMP_MODULES . | ssh admin@$TARGET tar xz --no-same-owner -C /usr/src/linux
```

### Using the Source with DKMS

1. Fix dangling build and source symlinks.

    ```bash
    cd /lib/modules/`uname -r`/
    rm build source
    ln -s /usr/src/linux source
    ln -s source build
    ```

2. Prepare the tools needed for dkms.

    ```bash
    cd /lib/modules/`uname -r`/build
    make prepare
    make modules_prepare
    ```

   Note that you may need to install the bc package on ARM targets.

3. Re-version the NI modules.

    ```bash
    dkms autoinstall
    ```

   If you get strange gcc errors during this step, ensure that the gcc
version used to build the kernel on the host machine is compatible
with the gcc version on the target. Check the output logs under:
/var/lib/dkms/<ni_module>/<version>/build/make.log.

7. (optional) Check dkms status.

    ```bash
    dkms status
    ```

8. Reboot the target.


**HELP! MY TARGET DOESN'T BOOT!**

If, after building and putting a new kernel on the target, you are unable
to boot successfully, refer to your controller's documentation on forcing
the controller to boot into safe mode and format from MAX.

*** NOTE ***
Changes to the kernel running on the target will be lost in certain operations
from MAX, including formatting the target and uninstalling all components.

