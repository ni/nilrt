NI Linux Real-Time Distribution
======

Introduction
------

Downloads the NI Linux Real-Time (NILRT) source code and
provides scripts to aid in building images and packages.

Build Steps
------

1. Get the source by running the following commands:

        git clone https://github.com/ni/nilrt.git
        cd nilrt
        git checkout nilrt/<release>
        ./nibb.sh update

2. Configure the build system for the machine architecture that you are
interested in. For example, running the command

        THREADS=16 DISTRO=nilrt MACHINE=x64 ./nibb.sh config

    results in a file called env-nilrt-x64. This file contains the
requisite environment variables to tell the bitbake/OE system to build
for the NILRT distribution for Intel x64-based NI controllers with 16
worker threads.

    Substituting MACHINE=xilinx-zynq for MACHINE=x64 configures an
environment for building NILRT for Xilinx Zynq-based NI controllers.

    If you omit the THREADS, DISTRO, or MACHINE variables, you will be
prompted to pick from a list of available options.

3. Build the package or packages that you want for your target. This
includes standalone image names (e.g. minimal-nilrt-image) and
standalone packages. For example, to build Python, Ruby, Apache, and
the minimal NILRT image, run the following commands:

        . env-$DISTRO-$MACHINE
        bitbake python ruby apache2
        bitbake minimal-nilrt-image

    **NOTE** Building packages through OpenEmbedded can use significant
disk space, on the order of tens of gigabytes. If you are preparing a
virtual machine to build images, make sure to allocate sufficient disk
space.

    The resulting ipk files that can be installed through opkg in the
case of standalone packages (e.g. python, ruby, apache2) exist at the
following directory:

        tmp-glibc/deploy/ipk/...

    If you build a complete image (e.g. minimal-nilrt-image), the
compressed root filesystem image can be found at the following
directory:

        tmp-glibc/deploy/images/...

4. (Optional/Advanced) Bitbake can transform deploy/ipk into a package
feed when you run the following command:

        bitbake package-index

    Your build machine can then host the feed by running the following
command:

        (cd tmp-glibc/deploy/ipk/ && python -m SimpleHTTPServer 8080)
        # press ctrl+c to stop hosting

    This creates a temporary HTTP server on port 8080 that is accessible
to other hosts on your local network. You may need to configure your
firewall to permit Python to access port 8080. Otherwise, the server
will only be accessible locally on address localhost:8080.

---

    Enjoy, and happy hacking!
    ni.com/community/
