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
