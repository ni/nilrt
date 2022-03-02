# NILRT Package Feeds


## The "Core" Feed


### packagegroup-ni-contributors

The "contributors" packagegroup contains packages which are dependencies of
NILRT community projects. Each dependency in this group must have a community
developer contact, who can speak to the technical requirement for the
dependency.

When a package in the contributors group fails to build for a non-trivial
reason, the NI RTOS team will disable the package and notify the technical
contact of the build failure. The technical contact will be responsible for
developing and submitting a fix for the failure.

A package being disabled in the contributors feed is not sufficient to delay a
NILRT release.


### packagegroup-ni-internal-deps

The "proprietary" packagegroup contains OE packages which are dependencies of
NI-proprietary IPKs, distributed via the "NIFeeds" (`ni-*/` on the package feed
server). Because the NIFeeds packages are built outside of OE, bitbake is not
able to automatically build these deps.

Each entry in the packagegroup must include the name of the NI-internal project
which has the dependency, and a technical contact for a developer who can speak
to the nature of the requirement.
