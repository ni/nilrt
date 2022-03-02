# NILRT Package Feeds

The NI-produced NILRT package feeds have the following structure:

```
${release}/
|-- ${arch}/
|   |-- main/         # The Core Feed
|   \-- extra/        # The Extra Feed
|-- ni-main/          # NIFeeds "Main" Feed
\-- ni-lv${release}/  # NIFeeds "Labview" release Feeds
```

----


## The Core Feed

`meta-nilrt.git:**/packagefeed-ni-core.bb`

The "core" package feed (`main/` on the package feed server) contains IPKs which
meet any of the following criteria:

* They are required to build any of the NILRT image recipes.
* They are open-source dependencies of NI-proprietary IPKs, distributed via the
  NIFeeds (see [packagegroup-ni-internal-deps](#packagegroup-ni-internal-deps)).
* They are dependencies of certain NILRT community projects (see
  [packagegroup-ni-contributors](#packagegroup-ni-contributors)).

The core feed is always built as a first stage to building NILRT images.
Packages from the feed-build artifacts are used (by way of opkg) to compose the
rootfs archive of the image recipes.

Accordingly, no recipes which are dependencies of the core feed are permitted to
fail during build.


### packagegroup-ni-contributors

`meta-nilrt.git:**/packagegroup-ni-contributors.bb`

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

`meta-nilrt.git:**/packagegroup-ni-internal-deps.bb`

The "proprietary" packagegroup contains OE packages which are dependencies of
NI-proprietary IPKs distributed via the "NIFeeds". Because the NIFeeds packages
are built outside of OE, bitbake is not able to automatically build these deps.

Each entry in the packagegroup must include the name of the NI-internal project
which has the dependency, and a technical contact for a developer who can speak
to the nature of the requirement.

----


## The Extra Feed

`meta-nilrt.git:**/packagefeed-ni-extra.bb`

The "extra" package feed (`extra/` on the package feed server) contains IPKs
which might be useful to NILRT users, but which are not officially supported by
NI.

There is no guarantee that packages in the extra feed:
* are functionally correct
* are present in any particular release of NILRT
* will be present in a future release of NILRT

NILRT users should not depend on packages from the extra feed for their
projects. If you are a community member who is willing to sponsor a package to
be distributed with the NI-built feeds, you may submit a PR adding your
dependency to `packagegroup-ni-contributors` (or contact the NI RTOS team for
more information).

----


## NIFeeds

The "NIFeeds" are IPK feeds maintained and built by NI client teams other than
the RTOS team. They provide NI-proprietary software which is probably not open
source or buildable through OpenEmbedded.


### ni-main

The `ni-main/` feed is LabVIEW-release-agnostic NI-proprietary IPKs.

Some `ni-main` feed content is required to enable NI workflows (like MAX
connectivity) for NILRT safemode and runmode images.


### ni-lv*

The `ni-lv${release}/` feeds contain NI-proprietary IPKs which are specific to a
particular release of LabVIEW, including content like the LabViEW runtime
itself.
