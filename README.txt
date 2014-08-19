National Instruments OpenEmbedded Image Creation scripts

The scripts contained within aid in building images and packages for
National Instruments NI Linux Real-Time targets.

1. Configure the build system for the machine architecture that you are
interested in, for example, running

     MACHINE=xilinx-zynq ./nibb.sh config

will results in a file "env-nilrt-xilinx-zynq" that contains the requisite
environment variables to tell the bitbake/OE system to build for the nilrt
distro (NI Linux Real-Time) for the Xilinx Zynq-based NI controllers.

If you omit the MACHINE variable, you will be prompted to pick from a
list of available machines.

2. Build the package or packages that are desired for your target. This
includes stand-alone image names (e.g. niconsole-image) as well as standalone
packages. For example, if you wanted to build python, you would run

     . env-$BRANCH-$MACHINE
     bitbake python

The resulting ipk files that can be installed through opkg in the case
of standalone packages exist at

    $NIBB_ROOT/build/tmp_$DISTRO_$MACHINE/deploy/ipkg/...

If you build a complete image, the compressed root filesystem image can be
found at

    $NIBB_ROOT/build/tmp_$DISTRO_$MACHINE/deploy/images/...

** NOTE **
Building packages through OpenEmbedded can use significant disk space,
on the order of tens of gigabytes. If you are preparing a virtual machine
to build images, make sure to allocate sufficient disk space.

Enjoy, and happy hacking!
ni.com/community/
