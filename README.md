# NI Linux Real-Time

## Introduction

This project builds packages and images for the NI Linux RT distribution.

NI Linux RT is a
[Real-Time-scheduling](https://rt.wiki.kernel.org/index.php/CONFIG_PREEMPT_RT_Patch)
enabled OS, for use on NI's embedded hardware devices. This project uses the
[OpenEmbedded](http://www.openembedded.org/wiki/Main_Page) framework to build
and package the kernel, software, images, and installation media which compose
NI Linux RT.

Community (non-NI) developers can use this project to build packages for
open-source software projects, which are installable to their existing NI Linux
RT devices - including custom Linux kernels and kernel modules.


## Entering the Bitbake Build Environment

This project uses the [pyrex](https://github.com/garmin/pyrex) tool to transparently provide most of the toolchain requirements needed to run bitbake. However, there are are still a few setup steps.

1. Checkout the source and initialize the project submodules.
    ```bash
    git clone https://github.com/ni/nilrt.git
    cd nilrt
    git checkout nilrt/$release
    git submodule init
    git submodule update --remote --checkout
    ```

2. [Install the docker engine](https://docs.docker.com/engine/install/) on your build host. If you can successfully run `docker run hello-world`, then you have everything you should need.

3. Build (or pull) the `build-nilrt` pyrex container image.
    ```bash
    bash ./docker/create-build-nilrt.sh  # will tag the image as build-nilrt:latest

    # Verification
    docker images build-nilrt:latest  # should print the image you just built
    ```

4. Enter the NILRT build environment. Sourcing the init script the first time will automatically setup your pyrex container shim.
    ```bash
    . ./ni-oe-init-build-env [--org]

    # Verification
    bitbake --version  # If this succeeds, you're done.
    ```

    <font color=lightgreen>[NI]</font> builders who are connected to the NI  corporate network should specify `-org` in their init script args, to provoke the script into adding the `ni-org.conf` snippet to your bitbake directory. External builders *should not* use `--org`.

---

    Enjoy, and happy hacking!
    ni.com/community/
