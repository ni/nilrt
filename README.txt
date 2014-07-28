National Instruments OpenEmbedded Image Creation scripts

The scripts contained within will aid in building images and packages for
National Instruments NI Linux Real-Time controllers.

To get started, configure the build system for the machine architecture
that you are interested in, for example, using a CompactRIO 9068 as an
example, running

    MACHINE=xilinx-zynq ./nibb.sh config

If MACHINE is omitted, the available machines will be printed.

This will result in a file "env-$DISTRO-$MACHINE" that contains
the requisite environment variables to tell the bitbake/OE system about the
machine you are building for.

At this point, for example, you can build the python packages for your target
with the commands

    . env-$BRANCH-$MACHINE
    bitbake python

Python is just an example of one package that could be built.

The resulting images (ipk files that can be installed through opkg) exist
at $NIBB_ROOT/build/images/ipkg/...

** NOTE **
Building packages through OpenEmbedded can use significant disk space,
on the order of tens of gigabytes! If you are preparing a (virtual) machine
to build images, make sure to allocate sufficient disk space.

Enjoy, and happy hacking!
ni.com/community/
