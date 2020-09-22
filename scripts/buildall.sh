#!/bin/bash

# Used for PR builds, build a variety of things
export MACHINE=x64
bitbake nilrt-dkms-image
bitbake packagegroup-ni-desirable

