# National Instruments Linux Real-Time OS

The scripts in this repo aid in building images and packages for the National Instruments NI Linux Real-Time OS.

## Building Recipes

### Cleaning the Workspace

If you are updating from a previous branch of nilrt, run the ``clean``
subcommand

```bash
./nibb.sh clean
```


### Configuration

| MACHINE     | DISTRO     | Image Recipe         | Description |
|-------------|------------|----------------------|-------------|
| x64         | nilrt-xfce | nixfce-image         | NILRT x86_64 runmode w/ XFCE
| x64         | nilrt-xfce | niconsole-image-safe | NILRT x86_64 safemode
| x64         | nilrt-xfce | nilrt-dkms-image     | NILRT x86_64 runmode w/ XFCE, dkms
| xilinx-zynq | nilrt      | niconsole-image      | NILRT ARM runmode

Configure the build system for the machine architecture that you are
interested in building.

```bash
MACHINE=$machine DISTRO=$distro ./nibb.sh config
```

This command will create a file ``env-$distro-$machine`` which contains
environment variables. Bitbake and OpenEmbedded need these variables to build
the NILRT distro for the ``$machine`` you specified.

If you omit any variables to control the desired build configuration (e.g.
machine or distribution), you will be prompted to select one from a list
of available options.

Once your environment files are created, you must ``source`` one from your shell
program before building recipes.

**Example**
```bash
MACHINE=xilinx-zynq DISTRO=nilrt ./nibb.sh config
# "env-nilrt-xilinx-zynq" is created
source ./env-nilrt-xilinx-zynq
```


### Building Recipes with Bitbake

From your configured shell environment, you can build packages, packagegroups,
and entire OS images, which can be installed to your NI Linux RT target. Do so
using the ``bitbake`` utility. Some example usage is given below, but you should
reference the [bitbake user
manual](https://www.yoctoproject.org/docs/latest/bitbake-user-manual/bitbake-user-manual.html)
for comprehensive documentation.

```bash
bitbake $recipe
#builds the package, packagegroup, or image defined in <recipe>
# ex.
#$ bitbake python3               # package
#$ bitbake packagegroup-ni-base  # packagegroup
#$ bitbake niconsole-image-safe  # image

bitbake -e $recipe
# parse $recipe and print the bitbake environment; do not build

bitbake --continue $recipe
# build $recipe, ignoring build errors for as long as is possible
```

For a collection of valid *packagegroups* provided by NI, reference the contents
of ``${NIBB_ROOT}/sources/meta-nilrt/recipes-core/packagegroups/``.

For a collection of valid *image* recipes provided by NI, reference the contents
of ``${NIBB_ROOT}/sources/meta-nilrt/recipes-core/images/``.

#### Packages and Packagegroups

The output of package and packagegroup recipes are ``.ipk`` package files, built
to a path like:

```bash
$NIBB_ROOT/build/tmp_${distro}_${machine}/deploy/ipk/
```

IPKs can be installed to your Linux RT target using the ``opkg`` package
manager.


#### Images

The output of *image* recipes are compressed root filesystem archives, built to
a path like:

```bash
${NIBB_ROOT}/build/tmp_${distro}_${machine}/deploy/images/
```

These are the same image archives used as the base for software installation
from NI's target provisioning tools. A proper NI installation also makes some
modifications to support NI software and installs closed-source software.

### Disk Space Warning

Building packages through Bitbake/OpenEmbedded can use a significant amount of
disk space, on the order of tens or hundreds of gigabytes. If you are preparing
a virtual machine to build images, make sure to allocate enough free disk space.

----

## The ARM Kernel

The kernel image created by the build system cannot be used on ARM targets.
If you will be compiling a custom kernel, see github.com/ni/linux for the
kernel source.  See KERNEL_SOURCE.txt in this directory for instructions
to build the kernel.

----

## Installing a Complete Image to an RT Target

1. Boot the target into safe mode. Refer to your hardware's manual for details
   on booting to safe mode.

2. If you are using a custom kernel, backup the NI-built kernel and modules.

```bash
/boot/linux_runmode.itb  # kernel location on ARM targets
/mnt/userfs/lib/modules/ # kernel modules
```

3. From the safe mode shell, reformat the run mode filesystem to using the
   ``nisystemformat`` utility.

```bash
# ARM targets
nisystemformat -f -t ubifs
# x86_64 targets
nisystemformat -f -t ext4
```

4. Unpack the rootfs archive to the run mode filesystem mount point (typically
   ``/mnt/userfs``).

5. Restore the NI-built kernel and module to their original locations in
   ``/boot`` and ``/mnt/userfs/lib/modules/`` **or** install your custom-built kernel as
   described in ``KERNEL_SOURCE.md``.

#### Logging In

NI's additions to the base image include scripts and other software affecting
login. To enable login without NI software, you will need to make a few more
changes. Assuming you are in safe mode and the run mode filesystem is mounted at
``/mnt/userfs``:

1. (ARM Only) Update the getty line in ``/mnt/userfs/etc/inittab`` to use
   ``ttyS0`` instead of ``ttyPS0``.

2. Provide a password for an account to use to log in (for example, if you
   want to log in as root, ``passwd -R /mnt/userfs root``).

----

Enjoy, and happy hacking!

ni.com/community/
