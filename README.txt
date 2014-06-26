National Instruments OpenEmbedded Image Creation scripts

The scripts contained within will aid in building images and packages for
National Instruments NI Linux Real-Time controllers.

To get started, configure the build system for the machine architecture
that you are interested in, for example, using a compactRIO 9068 as an
example, running

    MACHINE=xilinx-zynq ./nibb.sh configure xilinx-zynq

This will result in a file "env-$CURRENT_BRANCH-$MACHINE" that contains
the requisit environment variables to tell the bitbake/OE system about the
machine you are building for. It will be symlinked to env-nibb.

At this point, you can build the python packages for your machine with

    . env-nibb
    bitbake python

The resulting images (ipk files that can be installed through opkg) exist
at $NIBB_ROOT/build/images/ipkg/...

Enjoy, and happy hacking!
ni.com/community/
