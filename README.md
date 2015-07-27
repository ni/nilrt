National Instruments NI Linux Real-Time distribution
======

Introduction
------

Downloads National Instruments NI Linux Real-Time (NILRT) source and
provides script to aid in building images and packages.

Build Steps
------

1. Get the source by running

        git clone https://github.com/ni/nilrt.git
        cd nilrt
        git checkout nilrt/<release>
        ./nibb.sh update

2. Configure the build system for the machine architecture that you are
interested in, for example, running

        THREADS=16 DISTRO=nilrt MACHINE=x64 ./nibb.sh config

    results in a file "env-nilrt-x64" containing the requisite
environment variables to tell the bitbake/OE system to build for the
NILRT distribution for Intel x64-based NI controllers with 16 worker
threads.

    Substituting _MACHINE=xilinx-zynq_ for _x64_ configures an
environment for building NILRT for Xilinx Zynq-based NI controllers.

    If you omit _THREADS_, _DISTRO_ or _MACHINE_ variables, you will be
prompted to pick from a list of available options.

3. Build the package or packages that are desired for your target. This
includes stand-alone image names (e.g. minimal-nilrt-image) as well as
standalone packages (e.g. python). For example, if you wanted to build
Python, Ruby, Apache, and the minimal NILRT image, you could run

        . env-$DISTRO-$MACHINE
        bitbake python ruby apache2
        bitbake minimal-nilrt-image

    **NOTE** Building packages through OpenEmbedded can use significant
disk space, on the order of tens of gigabytes. If you are preparing a
virtual machine to build images, make sure to allocate sufficient disk
space.

    The resulting ipk files that can be installed through opkg in the
case of standalone packages (e.g. python, ruby, apache2) exist at

        tmp-glibc/deploy/ipk/...

    If you build a complete image (e.g. minimal-nilrt-image), the
compressed root filesystem image can be found at

        tmp-glibc/deploy/images/...

4. [optional/advanced] Bitbake can transform deploy/ipk into a package
feed by running

        bitbake package-index

    Your build machine can then host the feed by running

        (cd tmp-glibc/deploy/ipk/ && python -m SimpleHTTPServer 8080)
        # press ctrl+c to stop hosting

    to create a temporary HTTP server on port 8080 accessible to other
hosts on your local network. You may need to configure your firewall
to permit python access to port 8080. Otherwise, the server will only be
accessible locally (I.e. on address localhost:8080).

---

    Enjoy, and happy hacking!
    ni.com/community/
