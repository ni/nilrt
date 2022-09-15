# `estimate-usage` scripts
These scripts exist to allow developers to determine approximately how much disk
space will be used by a system image when it is deployed.

Note that the sizes returned are **approximate**. The estimation scripts don't
necessarily use the same software versions or command-line invocations that
happen on real targets.

## The platform-specific scripts
The `estimate-usage.<platform>.<image-type>.sh` scripts in this directory are
designed to consume system images and determine the disk space usage if their
contents are unpacked into the default filesystem of the platform.

### Running
These scripts consider every argument given to be an image to provide an
estimate for. If no arguments are given, they read from standard input. There is
no argument parsing: there are no command-line options, and an argument of `-`
does not indicate standard input.

### Privileges
These scripts assume that they will be executed with sufficient privileges to
perform mounts, write to device files, and (un)load kernel modules. For this
reason, they are intended to be run within a virtual machine. They will attempt
to clean up after themselves, but **may have unintended consequences**: for
instance, the runmode estimation script for ARMv7-A assumes that it creates the
ubi flash device `/dev/ubi0` and writes to it, so if that device already exists
you may suffer data loss.

### Software requirements
Running the scripts for ARMv7-A requires MTD and U-Boot tools for runmode and
safemode, respectively. On Debian, the packages can be installed with:

    apt-get install mtd-utils u-boot-tools

### Output format
The output of these scripts is a five-column TSV (tab-separated value) table on
standard output. The columns have the following meanings:

 1. The name of the image examined
 2. The CPU architecture (`x86_64` or `ARMv7-A`, assumed by the script)
 3. The type of image (`runmode` or `safemode`, assumed by the script)
 4. The type of measurement (`disk footprint` or `kernel + ramdisk`)
 5. The human-readable size in bytes, using binary-sized prefixes K, M, G, and
    so on.

## The top-level script
The `estimate-usage.sh` script here fetches the latest exports of the system
images, starts a virtual machine, and runs the platform-specific scripts within
the virtual machine to determine the space usage of those images.

### Running
This script ignores all arguments.

### Source of images
When the script searches for the latest exports, it looks in the network shares
on the NI corporate network. There are environment variables to control where
the searching starts:

 - `EXPORTS_DIR`: the location of `\\nirvana\perforceExports\build\exports`,
   defaulting to `/mnt/nirvana/perforceExports/build/exports`
 - `EXPORT_SEARCH_PATH_X86_64`: the package export location to search for the
   latest version of the x86_64 images, defaulting to
   `$EXPORTS_DIR/ni/rtos/rtos_nilinuxrt/official/export`.
 - `EXPORT_SEARCH_PATH_ARMV7_A`: the package export location to search for the
   latest version of the ARMv7-A images, defaulting to
   `$EXPORTS_DIR/ni/nilr/nilrt_os_common/official/export`.

There is no way to select a particular version to be searched for; the script
will always pick the version with the latest timestamp. This may be frustrating
if work is ongoing for multiple versions. If you would like to change this
behavior, modify the functions `get_latest_x86_64_images` and
`get_latest_armv7_a_images`.

### Software requirements
Running the script requires QEMU (for x86_64 guests) and an SSH client to be
available. The VM is started without graphics, so a display is not required. The
TCP port 2222 is used to communicate with the guest. On Debian, the packages can
be installed with:

    apt-get install qemu openssh-client

### Output format
As with the platform-specific scripts, the output is a TSV table on standard
output; however, the first column (the name of the image) is omitted as they
are fetched as part of operation and aren't part of what the user is after.

Additional messages are printed to standard error; they can be suppressed by
setting the `VERBOSE` environment variable to `false`.

### QEMU arguments
The script does not invoke QEMU with any acceleration arguments, so it might be
slower than you'd prefer. You can set the environment variable `QEMU_OPTIONS` to
pass extra arguments. For instance, if you want to use KVM, you can use

    QEMU_OPTIONS="-accel kvm" ./estimate-usage.sh

### VM image
When the script retrieves the disk image for the VM, by default it will copy it
to `$XDG_CACHE_HOME/nilrt-estimate-usage/vm-base.qcow2` to be a courteous
network user and speed up future runs of the script. There are no checks
performed to detemine if the image is stale. You can set the `USE_CACHE`
environment variable to `false` to force a download, but that will not clear the
cache.
