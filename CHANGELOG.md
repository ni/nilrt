# Changelog

This changelog consolidates changes for the [nilrt](https://github.com/ni/nilrt) repo, [meta-nilrt](https://github.com/ni/meta-nilrt) OE layer, and NI's branch of the [linux](https://github.com/ni/linux) kernel. Other OE layer changes are tracked in their respective changelogs.

The NI Linux Real-Time project uses a mainline branching model with product branches for stable releases.

This changelog attempts to conform to the changelog spec on [keepachangelog.org](https://keepachangelog.com/en/1.0.0/).

The evergreen, canonical changelog for *all NILRT branches* can be [found here](https://github.com/ni/nilrt/blob/HEAD/CHANGELOG.md).

## Latest Updates
* nilrt: 293
* meta-nilrt: 794
* linux: 184


----
## 11.0
Branch: `nilrt/25.0/scarthgap`

### nilrt
No changes.

### meta-nilrt
#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/663) `python3-schema` to the core packagefeed.
- [Added](https://github.com/ni/meta-nilrt/pull/663) the `utf8cpp` project to the meta-nilrt layer.
- [Added](https://github.com/ni/meta-nilrt/pull/717) `libpwquality` to the core packagefeed.
- [Added](https://github.com/ni/meta-nilrt/pull/726) `nftables` to runmode.
- [Added](https://github.com/ni/meta-nilrt/pull/729) `nilrt-snac` recipe to put system into SNAC configuration.
- [Added](https://github.com/ni/meta-nilrt/pull/782) the ability to upgrade opkg-keyrings to get the latest signing keys during the installation of BSI.
- [Added](https://github.com/ni/meta-nilrt/pull/775) opkg-keyrings visibility on MAX, now users can upgrade their keyrings directly from MAX.
- [Added](https://github.com/ni/meta-nilrt/pull/776) metadata parsing functionality to opkg-utils so it can read custom metadata in a package.
- [Added](https://github.com/ni/meta-nilrt/pull/792) a new signing key to the base system image.


#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/663) ni-grpc-device to `2.4.0`.
- [Changed](https://github.com/ni/meta-nilrt/pull/674) `egrep` calls in recovery media files to `grep -E`, as the former is deprecated.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/727) `libfmi` to `v3.0a4`

#### Deprecated
- [Deprecated](https://github.com/ni/meta-nilrt/pull/663) the `ntpdate` package, since it has been dropped by upstream.
- [Removed](https://github.com/ni/meta-nilrt/pull/673/commits/01ac041e848b67553001cee00336637eefb9384a) NIcurl-specific functions from curl, since these sources are no longer used by NIcurl.
- [Removed](https://github.com/ni/meta-nilrt/pull/675) the unused `efifix` scripts.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/676) a parsing error in the recovery media provisioning scripts.


----
## 10.4
Branch: `nilrt/24.8/kirkstone`

### nilrt
#### Added
- [Added](https://github.com/ni/linux/pull/170) nftables support to 6.1 and 6.6 kernels.

#### Security
- [Upgraded](https://github.com/ni/meta-openembedded/pull/65) `apache2` to 2.4.62 to fix CVE-2024-38476, CVE-2024-40725.

### Fixed
- [Fixed](https://github.com/ni/openembedded-core/pull/132) 2038 bug in `grub2`.

### meta-nilrt
#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/715) `patool` dependencies to the core packagefeed.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/709) a bug that could prevent system replication tool from working across versions.
- [Fixed](https://github.com/ni/meta-nilrt/pull/710) ktimers priority to improve nohz performance.
- [Fixed](https://github.com/ni/meta-nilrt/pull/721) system replication tool to work with image sizes larger than 4GB.
- [Fixed](https://github.com/ni/meta-nilrt/pull/722) ksoftirqd and rcu priority to address a priority inversion deadlock.


----
## 10.3
Branch: `nilrt/24.5/kirkstone`

### nilrt
#### Removed
- [Removed](https://github.com/ni/nilrt/pull/274) feed-changelogs, since we don't yet have a good usecase for their inclusion, and they have not proven to be useful.

### meta-nilrt
#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/694) a workflow to the provisioning tool to make and apply whole system images.


----
## 10.2
Branch: `nilrt/24.3/kirkstone`

### nilrt
#### Added
- [Added](https://github.com/ni/nilrt/pull/267) a `host_deply_ipks` script, to help developers host deploy IPK directories as opkg feeds.

#### Security
- [Fixed](https://github.com/ni/meta-virtualization/pull/19) `runc` CVE-2024-21626​.

### meta-nilrt
#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/652) `linux-nilrt-next` to `6.6`.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/667) `linux-nilrt-nohz` to `6.1`.
- [Changed](https://github.com/ni/meta-nilrt/pull/657) `fw_printenv` behavior, so that it no longer prints duplicate variable values.
- [Changed](https://github.com/ni/meta-nilrt/pull/677) `cifs-utils` to now RDEPEND on `keyutils`, which is a generally-required package for mounting cifs shares.


----
## 10.1
Branch: `nilrt/24.0/kirkstone`

### nilrt


### meta-nilrt

#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/628) libglu to core feed.

#### Changed
- [Moved](https://github.com/ni/meta-nilrt/pull/626) docker package from extras feed to core feed.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/622) a package-installation error with `cryptsetup`, where opkg could not satisfy the `lvm2-udevrules` dependency.
- [Fixed](https://github.com/ni/meta-nilrt/pull/623) a bug in the `linux-nilrt` recipes, which would stamp the kernel uname string with the incorrect build datetime.
- [Fixed](https://github.com/ni/meta-nilrt/pull/640) an issue where dkms drivers would not rebuild when multiple kernels are installed.
- The `ni-rtfeatures` initscript will now log the `poweron` reset_source string as a valid state, instead of [throwing an error](https://github.com/ni/meta-nilrt/pull/644).


----
## 10.0
Branch: `nilrt/23.8/kirkstone`

Beginning with this release, NILRT has been rebased to Yocto 4.0 "kirkstone".


### nilrt

#### Changed
- [Upgraded](https://github.com/ni/openembedded-core/pull/102) `pango` to 1.50.8, to pull some testing changes from upstream.

#### Deprecated
 - OpenSSH has been upgraded to a version which by default disables the use of insecure SHA1 signatures (referred to as `ssh-rsa`). See [their release notes](http://openssh.com/txt/release-8.8) for more information, including how to re-enable it.
    - This change is known to break compatibility with NI MAX versions prior to 22.5. Prior MAX releases used `libssh2` version 1.8, which relies upon SSH-RSA, causing MAX to throw a "Miscellaneous operation failure" when attempting to connect to a NILRT 10 system image. To work around, either: upgrade your NI MAX installation to 22.5 or later (recommended), or modify the NILRT target's `sshd_config` to re-enable `ssh-rsa` (see above link).

#### Security
- [Upgraded](https://github.com/ni/meta-openembedded/pull/37) `lldpd` to fix [`CVE-2021-43612`](https://nvd.nist.gov/vuln/detail/CVE-2021-43612).
- [Upgraded](https://github.com/ni/openembedded-core/pull/103) `ncurses` to 6.4 to fix [`CVE-2023-29491`](https://nvd.nist.gov/vuln/detail/CVE-2023-29491).
- [Upgraded](https://github.com/ni/meta-openembedded/pull/39) `c-ares` to 1.19.1 to fix CVE [`CVE-2023-32067`](https://nvd.nist.gov/vuln/detail/CVE-2023-32067).
- [Backported](https://github.com/ni/meta-qt5/pull/9) a patch to `qtbase` to fix [`CVE-2023-24607`](https://github.com/advisories/GHSA-gfrv-8477-wf9f).
- [Backported](https://github.com/ni/openembedded-core/pull/110) a patch to `libpcre2` to fix [`CVE-2022-41409`](https://nvd.nist.gov/vuln/detail/CVE-2022-41409).


### meta-nilrt
- meta-nilrt is now compatible with the OE "kirkstone" release.
- Where experimental RAUC content conflicted with NILRT 10 development, it [has been dropped](https://github.com/ni/meta-nilrt/pull/513). Do not expect any remaining RAUC content to be functional.
- NILRT builds will [now generate](https://github.com/ni/meta-nilrt/pull/567) SPDX SBOM files for packages and images.

#### Added
- Migrated some recipes to meta-nilrt, which were dropped from upstream meta-OE, as of kirkstone.
    - [python-nose](https://github.com/ni/meta-nilrt/commit/365f8514)
    - [python3-configparser](https://github.com/ni/meta-nilrt/commit/abb5b21f8d1f494446f93dcbc9b802700a514b16)
- [Added](https://github.com/ni/meta-nilrt/commit/bacb71b1) a uid/gid pair for `ossec`, to support installation of the `ossec-hids` package.
- [Added](https://github.com/ni/meta-nilrt/pull/605) the `bolt` package to provide a user-space application to manage Thunderbolt connections.
- [Added](https://github.com/ni/meta-nilrt/pull/612) the ability to set the `LVRT_CGROUP_VERSION` via the `/etc/default/lvrt-cgroup` init setting.

#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/499) the `syslog-ng` recipe to support syslog-ng v3.36.1.
- Converted several legacy python recipes to use the `setuptools3_legacy` compatibility bbclass from upstream yocto.
- The `util-linux` packages [now depend](https://github.com/ni/meta-nilrt/pull/505) on `busybox`, because we use initscripts from the latter.
- [Set](https://github.com/ni/meta-nilrt/pull/591) the meta-layer priority of meta-nilrt to `25`, to get it higher than the distro's subordinate layers.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/589) the `linux-nilrt-debug` kernel to base on Linux 6.1. `linux-nilrt-nohz` [will remain](https://github.com/ni/meta-nilrt/pull/621) on 5.15 for this release.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/601) the `linux-nilrt` kernel to base on Linux 6.1.

#### Deprecated
- [Dropped](https://github.com/ni/meta-nilrt/commit/d1e98a5331ba34866c1eb41537bf9267c6a7178a) the meta-nilrt `apr` bbappend, since it broke recipe `do_compile` and didn't seem to have a purpose.
- [Dropped](https://github.com/ni/meta-nilrt/commit/c8809128) the `ni-refpolicy` SELinux security reference policy, because it wasn't maintainable and didn't have a clear owner.
- Dropped ([1](https://github.com/ni/meta-nilrt/commit/037f9e09), [2](https://github.com/ni/meta-nilrt/commit/82dbf99d)) .patches from the `wpa-supplicant` recipe which conflicted with kirkstone and don't add apparent value.
- [Replaced](https://github.com/ni/meta-nilrt/pull/592) the obsolete and unmaintained `pycrypto` library, with the `pycryptodome` alternative.
- [Removed](https://github.com/ni/meta-nilrt/pull/600) the `python3-pysnmp` package, because it has poor support and is unneeded.
- [Removed](https://github.com/ni/meta-nilrt/pull/605) the `tbtadm` package, in favor of `bolt`.
- [Deprecated](https://github.com/ni/meta-nilrt/pull/616) the `dsa` host-key from being used in the default `openssh` server configuration, due to its relative insecurity.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/500) a sporadic `glibc:do_package` error, caused by the `stashed-locale` directory dropping out of the recipe-build workspace.
- [Fixed](https://github.com/ni/meta-nilrt/commit/625e1c3d) a bug in the `linux-kernel-debug:do_install` where the recipe sourced kernel debug symbols from the wrong path.
- [Fixed](https://github.com/ni/meta-nilrt/pull/562) some salt incompatibilities with the python3.10 runtime, which broke software installation workflows using sysapi and SystemLink.
- [Increased](https://github.com/ni/meta-nilrt/pull/611) the `RCVBUF` buffer size for busybox's ifplugd implementation, to fix a possible configuration failure on systems with very large numbers of network interfaces.
- [Fixed](https://github.com/ni/meta-nilrt/pull/614) an incompatibility between LabVIEW and the `status_led` binary in `ni-utils`, which prevented the status LED from blinking when an LVRT startup app crashes.


----
## 9.4
Branch: `nilrt/23.5/hardknott`

### meta-nilrt

#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/569) `dkms` to version 3.0.10, to resolve spurious warnings when compiling unversioned kernel modules.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/570) the preview kernel (`kernel-next`) to version 6.1.


----
## 9.3
Branch: `nilrt/23.3/hardknott`

The NILRT 9.3 release is a regular quarterly release of the distribution, based on OE "hardknott". The majority of changes in this release are improvements to the NI-internal functional and performance validation test suites.


### nilrt
#### Changed
- The `create-build-nilrt.sh` script [now allows](https://github.com/ni/nilrt/pull/213) the user to override the NILRT codename (image tag).
- Opkg feed signing now [uses the 2023 signing key](https://github.com/ni/meta-nilrt/pull/535).


### meta-nilrt
#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/541) the `nvme-cli` package to the extras/ feed.


#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/515) `dkms` recipe version to v3.0.9, to consume upstream improvements to autoinstall error handling.
- [Moved](https://github.com/ni/meta-nilrt/pull/518) the `rwlockbomb` test to its own package, as it was not reliable-enough for inclusion in the `glibc-tests` package.
- The RT priority of `irq_work` threads is now [set](https://github.com/ni/meta-nilrt/pull/504) to 15 in `rtctl`.


#### Deprecated
- [Removed](https://github.com/ni/meta-nilrt/pull/519) the `irq_test_priority.sh` ptest, as the NI-specific linux subcomponent it was testing has [been deprecated](https://github.com/ni/linux/pull/91) in the kernel.


----
## 9.2
Branch: `nilrt/23.0/hardknott`


### nilrt
- The cross-compile toolchain build target - which was previously exported manually to the [ni.com support section](https://www.ni.com/en-us/support/downloads/software-products/download.gnu-c---c---compile-tools-x64.html#338442) - can now be built directly from OE using the `:scripts/pipeline/build.toolchain.sh` script.


#### Added
- [Added](https://github.com/ni/nilrt/pull/197) a new pipeline script to build the NILRT toolchain *for linux* (`meta-toolchain` target).
- [Added](https://github.com/ni/nilrt/pull/199) a new pipeline script to build the NILRT toolchain *for Windows*.
- [Re-added](https://github.com/ni/nilrt/pull/198) the `meta-mingw` layer, since it is once again needed to build the meta-toolchain target.


#### Deprecated
- [Removed](https://github.com/ni/nilrt/pull/180) deprecated dist-feed creation scripts.


### meta-nilrt
- Meta-nilrt now supports building the `meta-toolchain` target.


#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/463) the `ni-configpersistentlogs` package, which will force system logs to persist between reboots when [enabled via nirtcfg](https://nilrt-docs.ni.com/troubleshooting/logs.html#enabling-persistent-logs).
- [Added](https://github.com/ni/meta-nilrt/pull/495) `meta-mingw` to the bblayers.


#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/465) the `linux-nilrt-next` preview kernel to 6.0.
- Small recipe `SRC_URI` fixes throughout this release to accommodate upstream Github branch changes.
  - [lsb](https://github.com/ni/meta-nilrt/pull/466)
- In preparation for Yocto "kirkstone" support, [updated](https://github.com/ni/meta-nilrt/pull/467) meta-nilrt recipes to use the new variable override syntax.
- ptest changes
  - [Generally improved](https://github.com/ni/meta-nilrt/pull/476) the accuracy of the `test_kernel_security` ptest in `kernel-tests`.
  - i915 ptests are now [skipped](https://github.com/ni/meta-nilrt/pull/479) on devices without an i915 video adapter.
  - [Added](https://github.com/ni/meta-nilrt/pull/478) new ptest to `kernel-tests` which validates serial port numbers.
  - Added several new ptests and changed some performance ptest workflows to upload their results to NI-domain test aggregation services. In non-NI environments, these tests should gracefully avoid sending out this data.
- [Moved](https://github.com/ni/meta-nilrt/pull/487/commits/ed1dae490a5ffdbe40a18b2b669a2b994cef1df5) the `ntp` package to `packagegroup-ni-desirable`.


#### Deprecated
- [Deprecated](https://github.com/ni/meta-nilrt/pull/474) the NI-specific `Packages.filelist` feed file, because it was unused.
- [Deprecated](https://github.com/ni/meta-nilrt/pull/486) ARM- and `nilrt-nxg`-specific recipe logic in several recipes.


#### Fixed
- [Removed](https://github.com/ni/meta-nilrt/pull/475) a non-existent dependency which blocked installation of the `util-linux-nilrt-ptest` package.
- [Fixed](https://github.com/ni/meta-nilrt/pull/517) a bug in opkg GPG key validation where package indexes fail to validate if the system clock time is too far in the past.


#### Removed
- [Removed](https://github.com/ni/meta-nilrt/pull/481) unused and unsupported recipes: `opencv`, `ptest-runner`, `nisdbootconfig`, and `expand-disk`.

----
## 9.1
Branch: `nilrt/22.8/hardknott`

### nilrt

#### Added
- Added NILRT GRUB version 22.8 to dist feed
- Added scripts to diff feeds between NILRT releases

#### Removed
- Moved styleguide information from CONTRIBUTING to meta-nilrt instead

#### Fixed
- [Fixed](https://github.com/ni/linux/pull/75) USB Ethernet breakage for cRIO-903x targets.

### meta-nilrt
See the [feed changelog](./docs/feed-changelog.md) for all updates to packages.

#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/427) `dkms`.
  - [Upgraded](https://github.com/ni/meta-nilrt/pull/455) to v3.0.6.
- [Added](https://github.com/ni/meta-nilrt/pull/450) a boot-time message to display the CPLD reset source.

#### Changed
- In `packagegroup-ni-base`:
  - [Added](https://github.com/ni/meta-nilrt/pull/419) `modutils-initscripts`.
  - [Added](https://github.com/ni/meta-nilrt/pull/429) `efibootmgr`.
- [Removed](https://github.com/ni/meta-nilrt/pull/422) `ni-rtlog` from the base image.
  - [Removed](https://github.com/ni/meta-nilrt/pull/434) the now-unnecessary `ni-lv2020` feed.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/432) Linux kernel version to 5.15.
- [Added](https://github.com/ni/meta-nilrt/pull/435) configuration file for `libpam`.
- [Replaced](https://github.com/ni/meta-nilrt/pull/452) per-mitigation configuration options with a global toggle. If subsets of mitigations are desired, a configuration file is available.
- [Enabled](https://github.com/ni/meta-nilrt/pull/453) unlimited core dumps for debugging use cases.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/424) `openvpn` wrapper scripts sourcing configuration from an incorrect location.
- [Fixed](https://github.com/ni/meta-nilrt/pull/425) `getty` running on preexisting ttys.
- [Fixed](https://github.com/ni/meta-nilrt/pull/430) `xfce-nilrt-settings` referring to an incorrect location, which prevented programs from showing up in right-click menus.

#### Removed
- [Removed](https://github.com/ni/meta-nilrt/pull/439) several connectivity packages.
- [Removed](https://github.com/ni/meta-nilrt/pull/440) several devtool packages.

----

## 9.0
Branch: `nilrt/22.5/hardknott`

### nilrt

#### Added
- Added [Pyrex](https://github.com/garmin/pyrex) usage for build containers to manage dependencies and versions.

#### Changed
- Rebased OE layer submodules from the OE/`sumo` release stable branches, to the OE/`hardknott` branches - where available.
  - A full list of the upstream changes between OE/sumo (yocto 2.5) and OE/hardknott (yocto 3.3) can be found in the Yocto project documentation's [Migration Guide](https://docs.yoctoproject.org/migration-guides/index.html).
  - glibc is [kept at 2.24](https://github.com/ni/openembedded-core/pull/56) (`sumo` version) as 2.33 (`hardknott`'s version) has a locking bug on RT applications.
- Upgraded the bitbake submodule to bitbake `1.50.2`.
- [Upgraded](https://github.com/ni/nilrt/pull/73) the nilrt-build dockerfile to a debian 10 base.
  - Added a more user-friendly way to enter the docker build container using `docker-compose`.
- [Updated](https://github.com/ni/meta-nilrt/pull/377) inode size in filesystem to support dates past year 2038.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/308) an issue where SSH sessions were not properly closed on reboot or shutdown.

#### Removed
- Removed the following OpenEmbedded Layers either because they were abandoned upstream, or because official support was dropped within NILRT.
  - [meta-ivi](https://github.com/ni/nilrt/pull/119).
  - [meta-java](https://github.com/ni/nilrt/pull/120).
  - [meta-measured](https://github.com/ni/nilrt/pull/127).
  - [meta-mingw](https://github.com/ni/nilrt/pull/124).
  - [meta-mono](https://github.com/ni/nilrt/pull/123).

### meta-nilrt

#### Changed
- `gcc` has been upgraded to version `10.2`.
- `openssl` has been upgraded to `1.1.1k`.
- `python2` support has been totally deprecated in favor of `python3`.
- [Replaced](https://github.com/ni/meta-nilrt/pull/316) `packagegroup-ni-xfce` with `packagegroup-ni-graphical` which includes the former.
- [Upgraded](https://github.com/ni/linux/pull/64) the `linux` kernel to `5.10.115-rt67`.
- Changed the available images to build. The following images are recommended when building NI Linux Real-Time.
  - `nilrt-base-system-image` - The base system image for runmode.
  - `nilrt-recovery-media` - The recovery media/safemode installation iso.

#### Removed
- [Removed](https://github.com/ni/meta-nilrt/pull/277) the `restore` images and `lvcomms` images. The distributions that required these images are not supported in newer versions.
- [Removed](https://github.com/ni/meta-nilrt/pull/355) boot attestation based on now dead upstream code.
- [Removed](https://github.com/ni/meta-nilrt/pull/290) packages dropped from upstream.


----
## 8.22
Branch: `nilrt/25.0/sumo`

### nilrt

No changes.

### meta-nilrt

- [Added](https://github.com/ni/meta-nilrt/pull/792) new signing key into opkg-keyrings.


----
## 8.21
Branch: `nilrt/24.8/sumo`

No changes.


----
## 8.20
Branch: `nilrt/24.5/sumo`

No changes.

----
## 8.19
Branch: `nilrt/24.3/sumo`

No changes.


----
## 8.18
Branch: `nilrt/24.0/sumo`

No changes.


----
## 8.17
Branch: `nilrt/23.8/sumo`

**Note**: this version was not propagated to the 23.8 system image installers. Running the 23.8 installer will install the 8.16/23.5 ARM base system image.

### meta-nilrt
#### Changed
- Socketcan interfaces will [no longer](https://github.com/ni/meta-nilrt/pull/587) be started with ifplugd.


----
## 8.16
Branch: `nilrt/23.5/sumo`

### nilrt
#### Changed
- [Upgraded](https://github.com/ni/meta-openembedded/pull/34) `syslog-ng` from 3.8.1 to 3.31.2, to consume upstream fixes to a slow memory leak on SIGHUP.


----
## 8.15
Branch: `nilrt/23.3/sumo`

### nilrt
#### Changed
- Opkg feed signing now [uses the 2023 signing key](https://github.com/ni/meta-nilrt/pull/537).


----
## 8.14
Branch: `nilrt/23.0/sumo`


### meta-nilrt

#### Deprecated
- [Deprecated](https://github.com/ni/meta-nilrt/pull/488) the NI-specific `Packages.filelist` feed file, because it was unused.


----
## 8.13

Branch: `nilrt/22.8/sumo`

The 8.13 release is a regular release of the NI LinuxRT "sumo" mainline, supporting all ARM32 hardware.

### nilrt

#### Fixed
- [Fixed](https://github.com/ni/nilrt/commit/979c1003) an error in the extra feed build pipeline script which referenced the wrong recipe name.


----

## 8.12
Branch: `nilrt/22.5/sumo`

The 8.12 release is a regular, quarterly release of NI LinuxRT. It primarily contains minor improvements and bug fixes to OE-sumo-based release images.


### nilrt

#### Added
- [Added](https://github.com/ni/nilrt/pull/142) pyrex support so that builds happen in a container.


### meta-nilrt

#### Changed
- [Updated](https://github.com/ni/meta-nilrt/pull/395) default machine to `xilinx-zynq`


### openembedded-core

#### Fixed
- [Fixed](https://github.com/ni/openembedded-core/pull/59) an issue where opkg's stderr output ends up in opkg status file.


----

## 8.11
Branch: `nilrt/21.8/sumo`

The 8.11 release is a regular, quarterly release of NI LinuxRT. It primarily contains bug fixes to the OE-sumo-based release images. Most development was performed in 2022 Q1.


### nilrt

#### Added
- [Added](https://github.com/ni/nilrt/pull/117) a `CONTRIBUTING` file with a Developer Certificate of Origin agreement.

#### Fixed
- Audited recipes throughout the meta-layers and, where needed, switched the github recipe source lines to use `https` as their transport protocol. This accommodated GitHub deprecating their `git` transport endpoints.


### meta-nilrt

#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/288) `opkg` to version `0.5.0`.
- [Moved](https://github.com/ni/meta-nilrt/pull/327) `tbb` from the `extra/` feed to `main/`.
- [Upgraded](https://github.com/ni/linux/pull/59) the `linux` kernel from `5.10.83-rt58` to `5.10.106-rt64`.
    - [Fixed](https://github.com/ni/linux/commit/051c9569fc919a173fbc7a56c75efdbba3b13b8c) [an issue](https://github.com/ni/linux/issues/44) in `buildnipkg` which prohibited booting on roboRIO-2.0.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/320) a `busybox` incompatibility in the `update-ca-certificates` script.
- [Fixed](https://github.com/ni/meta-nilrt/pull/326) NILRT's static uid/gid assignments to deconflict static assignments from colliding with dynamically created accounts.
- [Fixed](https://github.com/ni/meta-nilrt/pull/332) a build failure in the `libxkbcommon` package. It, and the rest of the `qtbase` dependencies should now be provided in the `main/` package feed.`


### openembedded-core

### Changed
- [Upgraded](https://github.com/ni/openembedded-core/pull/39) `opkg` and `opkg-utils` to version `0.5.0`.
    - `libsolv` upgraded to `0.7.17`.
- [Upgraded](https://github.com/ni/openembedded-core/pull/42) `ca-certificates` to `20211016` to resolve a revoked Mozilla DST certificate which caused malformed codepaths to execute in openssl.

### Fixed
- [Fixed](https://github.com/ni/openembedded-core/pull/48) kernel modules being errantly marked as configuration files in opkg.


----

## 8.10
Branch: `nilrt/21.5/sumo`

### meta-nilrt

#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/271) the unsupported preview of newer kernel (that is installable via `packagegroup-ni-next-kernel`) to 5.15.
- [Changed](https://github.com/ni/meta-nilrt/pull/265/files) repo fetch protocol in the sources for NI hosted repos from git to https after github [removed support](https://github.blog/2021-09-01-improving-git-protocol-security-github/) for unencrypted git protocol.

#### Fixed
- [Fixed](https://github.com/ni/grub/commit/61a02ce279575ea846e6ee7f8c9fb686fd54328c) GRUB implementation on some hardware by adding support for 64-bit linear frame buffer address.
- [Fixed](https://github.com/ni/meta-nilrt/pull/279/commits/812da23e7d3ef66df360faf32a3a86992dc0f281) a bug in `opkg` that causes multiple `opkg` processes to use the same volatile cache directory causing package installation failures.

----


## 8.9
Branch: `nilrt/21.3/sumo`

The NI LinuxRT 8.9 release upgrades the x64 architecture linux kernel version to 5.10, and is otherwise a bug-fix release for the sumo mainline.


### meta-nilrt

#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/195) the `pstore-save` utility; which mimicks the functionality of `systemd-pstore`.

#### Changed
- [Disabled](https://github.com/ni/meta-nilrt/pull/206) lockdep in the `linux-nilrt-debug` kernel, so that non-GPL modules (like `ni-kal`, et al.) can be installed when using the debug kernel.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/212) the NILRT x64 linux kernel version to 5.10.
    - The NILRT ARM kernel [will remain](https://github.com/ni/meta-nilrt/commit/1eac98d48b29330ffe5ed6d2ea5a76ee529d909a) on linux 4.14 for the time being.
- [Upgraded](https://github.com/ni/meta-nilrt/pull/194) `uboot` to `uboot_2017`; support for the *Elvis III* device.

### Deprecated
- [Disabled](https://github.com/ni/meta-nilrt/pull/213) `perf` scripting support on NILRT ARM, because it conflicts with the x64 kernel's 5.10 version.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/191) an opkg bug where unprivileged users would receive an error code when trying to perform operations which should not require root privileges.
- [Fixed](https://github.com/ni/meta-nilrt/pull/192) a bug where installing the `elfutils-dev` package could break subsequent DKMS module compilations.
- [Fixed](https://github.com/ni/meta-nilrt/pull/196) a bug with NILRT provisioning, where the provisioning tool would mistakenly install its payload to an onboard eMMC block device which is not the primary device storage.
- [Fixed](https://github.com/ni/meta-nilrt/pull/203) an `fw_printenv` bug, where value strings which include an `=` symbol would be insanely truncated during output.
- [Fixed](https://github.com/ni/meta-nilrt/pull/240) an obscure error with kernel module compilation on systems with system clocks set to a time before the `kernel-devsrc` IPK package file was packed.

----


## 8.8
Branch: `nilrt/21.0/sumo`


### NILRT

#### Removed
- [Deprecated](https://github.com/ni/nilrt/pull/53) and removed the [meta-orgconf](https://github.com/ni/meta-orgconf) layer from the project submodules. OE content from that layer has been moved into meta-nilrt, and configuration content has been moved to nilrt.git.

  NI-internal builders should source the [`ni-oe-init-build-env`](https://github.com/ni/nilrt/blob/nilrt/20.7/sumo/ni-oe-init-build-env) script with the `--org` option, to enable organization-specific bitbake configuration settings.


### meta-nilrt

#### Added
- [Added](https://github.com/ni/meta-nilrt/pull/164) a `packagegroup-ni-nohz-kernel` packagegroup and a version of the kernel with `NO_HZ_FULL` enabled, for customers who have strict real-time performance requirements.
- [Added](https://github.com/ni/meta-nilrt/pull/171) a strongswan VPN 5.x recipe (unsupported).
- [Added](https://github.com/ni/meta-nilrt/pull/173) a grpc-device server implementation (`ni-grpc-device`) for NI drivers which use grpc for network communication.

#### Changed
- [Upgraded](https://github.com/ni/meta-nilrt/pull/150) `u-boot-fw-utils`.
- [Changed](https://github.com/ni/meta-nilrt/pull/156) the opkg feed URI syntax for the distro, to always include the release minor rev, even if it is `0`. This release will use the string `2021.0`.
- [Updated](https://github.com/ni/meta-nilrt/pull/160) XFCE art assets to reflect the new company identity.

#### Fixed
- cURL:
    - [Fixed](https://github.com/ni/meta-nilrt/pull/165) an API break in cURL which caused some PharLAP installations to fail.
- kernel-devsrc:
    - [Fixed](https://github.com/ni/meta-nilrt/pull/192) a misconfiguration in the `kernel-devsrc` recipe which caused dkms (re)compilation to fail in cases where the `elfutils-dev` package is installed.


----


## 8.7
Branch: `nilrt/20.7/sumo`


### meta-nilrt

#### Added
- [Added](https://github.com/ni/meta-nilrt/commit/4e075099adf828d17fd9c111c043efdba55247f1) an unsupported preview of newer kernel bases (currently 5.10) via the `packagegroup-ni-next-kernel` recipe.
  - Kernel development headers for the `-next` kernel [are distributed](https://github.com/ni/meta-nilrt/commit/0ce447888ee09add1a8f83656b102e32d7af50a5) via the `kernel-devsrc-next` recipe.

#### Changed
- Kernel development headers [are now](https://github.com/ni/meta-nilrt/pull/63) distributed via the `kernel-devsrc` package.

#### Fixed
- [Fixed](https://github.com/ni/meta-nilrt/pull/127) a trivial error during early init about not being able to capture the `fw_printenv.lock`.

----


## 8.6
Branch: `nilrt/20.6/sumo`

### NILRT

#### Changed
- [Upgraded](https://github.com/ni/openembedded-core/commit/a4323b4c193296d499489567b79992c4760fcbc8) curl version to 7.72.0
- [Upgraded](https://github.com/ni/openembedded-core/commit/ed07362455e469415db3fed805faabcac58bfefb) openssl version to 1.0.2u

#### Deprecated
- [Drop support](https://github.com/ni/meta-nilrt/commit/1e6453ebca8735de96eaaf3bc931d22998c8dfb3) for VxWorks in curl and openssl

#### Security
- curl fixes
  - CVE-2018-16839 SASL password overflow via integer overflow
  - CVE-2018-16840 use-after-free in handle close
  - CVE-2018-16842 warning message out-of-buffer read
  - CVE-2018-16890 NTLM type-2 out-of-bounds buffer read
  - CVE-2019-15601 file: on Windows, refuse paths that start with \\
  - CVE-2019-3822  NTLMv2 type-3 header stack buffer overflow
  - CVE-2019-3823  SMTP end-of-response out-of-bounds read
  - CVE-2019-5435  Integer overflows in curl_url_set
  - CVE-2019-5436  tftp: use the current blksize for recvfrom()
  - CVE-2019-5481  FTP-KRB double-free
  - CVE-2019-5482  TFTP small blocksize heap buffer overflow
  - CVE-2020-8231  libcurl: wrong connect-only connection
- openssl fixes
  - CVE-2018-0732
  - CVE-2018-0734
  - CVE-2018-0737
  - CVE-2018-5407
  - CVE-2019-1547
  - CVE-2019-1552
  - CVE-2019-1559
  - CVE-2019-1563


### meta-nilrt

#### Added
- Minimal support for packaging multiple kernel versions in the same IPK feed configuration. (336ae54c5306d79e6c6a7cbbb02c79cab5b93012)
- IPK Extras Feed Content:
  - [makedumpfile](https://github.com/ni/meta-nilrt/commit/e4e53bac675ae710cc6ce676d170c8b91b1d719d)

#### Fixed
- Fixed a bug where 8.5 safemodes would error during MAX software installation to pre-8.5 runmodes. ([PR #46](https://github.com/ni/meta-nilrt/pull/46))

### linux
#### Changed
- Change `NR_CPUS` to 64 (the default) to support devices with more than 16 cores. (997fc3df5a3e740f585e6298cae9bd9d63832f7a)

----


## 8.5
Branch: `nilrt/20.5/sumo`

### meta-nilrt

#### Added
- Add the `/etc/machine-info` file vi the `base-files` package. It conforms to the [FreeDesktop machine-info](https://www.freedesktop.org/software/systemd/man/machine-info.html) spec and provides a canonical location to store the system comment.

#### Changed
- Reconfigure `/var/cache` as a non-volatile storage location, since small memory devices might otherwise run out of memory while installing large IPKs. (20ea59ab3e8938e8f45f5e073a315b75d4b7ec0f)

#### Fixed
- Fixed a race condition between NVMe enumeration and root mounting in the initramfs, which could affect PXIe-8881 devices with NVMe storage. (b420fca37b7d72d553356c310bacc6ba1aa1f4fc)
- glibc: Fix an `EAGAIN` retry loop in the PI Condvars patchset. (e9c9843b4b3d51a2ec0326b0bb388af56d1c76ac)

----


## 8.1
Branch: `nilrt/20.1/sumo`

### meta-nilrt

#### Added
- Added `perf` packages to the `packagegroup-ni-desirable`. (e0a6a88b02ec4d2db25fd3c916e7f8a4b45d3bb0)
- Added the `systemimageupdateinfo` script, which interrogates the system state to determine which NILRT bootflow is in use. (5001fee264c1e98d4176a2565542dcc5e5894a11)

#### Fixed
- Network file shares are now unmounted at shutdown. (d9a2c5d4f93cafb43e2094c567ae4d0e067b7a0c)

----


# Historic Changelog

Adapted from the legacy [Feature Updates and Changelog](https://forums.ni.com/t5/NI-Linux-Real-Time-Documents/Feature-Updates-and-Changelog-for-NI-Linux-Real-Time/ta-p/3532049?profile.language=en) document on forums.ni.com.

----


## 8.0
Branch: `nilrt/20.0/sumo`
### Changed
- Linux kernel updated to 4.14.146-rt67

## 7.0
Branch: `nilrt/19.0`
### Added
- [x64] Added support for some PXIe controller models (PXIe-8880, PXIe-8861, and PXIe-8840QC)
- [x64] Added DKMS support for supported PXIe and SystemLink-enabled controllers

### Changed
- Linux kernel upgraded to 4.14.87-rt49
- OE/Yocto upgraded to Sumo (2.5)
- GCC upgraded to 7.3.0
- OpenSSL upgraded to 1.0.2o
- Default python runtime upgraded from 2.7 to 3.5

## 6.0
Branch: `nilrt/18.0`
### Added
- Added the `tpm2-tools` packages to the feed, for interacting with tpm2

### Changed
- Linux kernel upgraded to 4.9.47-rt37
- OE upgraded to Pyro (2.3)
- GCC upgraded to 6.3
- glibc upgraded to 2.24
- OpenSSL upgraded to 1.0.2k


## 5.0
Branch: `nilrt/17.0`

### Added
- Added the salt project to the package feeds, to support the [SystemLink Early Access Release](https://saltstack.com/salt-open-source/)

### Changed
- Linux kernel upgraded to 4.6.7-rt14
- OE upgraded to Krogoth (2.1)
- GCC upgraded to 5.3
- glibc upgraded to 2.23
- OpenSSL upgraded to 1.0.2h
- nodejs upgraded to v4.4.3
- bluez5 upgraded to v5.4.2


## 4.0
Branch: `nilrt/16.0`

### Added
- Notable new packages in the opkg feed:
    - bluez5
    - gnuradio
    - Java JVM
    - libvncserver
    - mono
    - opencv 3.0
    - openjdk
    - ptpd
    - wireless-tools
    - x11vnc

## Changed
- Linux kernel upgraded to 4.1
- OE upgraded to Fido (1.8)
- glibc upgraded to 2.21
- GCC upgraded to 4.9
- OpenSSL upgraded to 1.0.2d

## 3.0
Branch: `nilrt/15.0`

### Added
- Notable new packages in the opkg feed:
    - Servers like apache2 as well as other light-weight webservers (lighttpd, nginx, cherokee, hiawatha, monkey, nostromo)
    - Useful tools to work with web-based workflows and existing web applications like php, fcgi (fast cgi), json-c, nodejs, improved python support (jinja2, mako, cloudeebus, autobahn, etc.), ruby
    - Improved python support (numpy, pycrypto, matplotlib, slip-dbus, etc.)
    - Requested libraries/applications (libopencv/opencv, libarchive, libcap, libcgroup, libsensor/lmsensor)
    - Improved tools for working with existing text-based projects (cmake, cgdb)
    - Improved python support (numpy, pycrypto, matplotlib, slip-dbus, etc.)
    - Requested libraries/applications (libopencv/opencv, libarchive, libcap, libcgroup, libsensor/lmsensor)
    - Improved tools for working with existing text-based projects (cmake, cgdb)
- To provide a browser-based way to read syslog files, there is now a 'System Log Viewer' tab in the NI Web-Based Configuration and Monitoring page for NI Linux RT Targets. LabVIEW 2015 also provides an API to write to SysLog, allowing system administrators a way to output debugging information, browse the log, and download entire logs remotely without the console or Linux domain expertise.

### Changed
- Linux kernel upgraded to 3.14
- We've switched away from the Xilinx-provided xemacps driver onto the Cadence macb driver for the ethernet controller, as it has seen more runtime in more platforms, and is supported by the upstream Linux kernel community
- eglibc upgraded to 2.20
- libssl upgraded to 1.0.1m
- python runtime upgraded to 2.7.9
- gcc upgraded to 4.8

## 2.0
Branch: `nilrt/14.0`

### Added
- Add support for the Intel x86_64 architecture.
    - Enables support of new targets; one example is the Performance CompactRIO
    - x86_x64 devices rely on an updated LTSI 3.10 based kernel which includes updates to PREEMPT_RT. Note that ARM devices still use the 3.2 based kernel.
    - x86_x64 devices use the ext4 journaling file system
    - x86_x64 devices use a UEFI BIOS
    - x86_x64 devices use GRUB 2 as the bootloader, as opposed to U-Boot on ARM devices x86_x64 devices support an XFCE desktop environment, which enables display and HMI use cases through a monitor directly cabled to the device. Learn more about HMIs at http://www.ni.com/white-paper/12602/en/
- NI Package Repository
    - Users can now get Linux packages from NI, instead of relying on the un-maintained Angstrom repositories. The update to the NI hosted package repository is automatically done when users upgrade the software on their devices to 2014. The repository can be manually browsed at download.ni.com/ni-linux-rt
- NI Source Repository
    - Users can now easily pull down the NI Linux RT kernel. Useful and convenient for advanced users intending to make customizations to the distribution. Available at github.com/ni
- On Target Module Versioning
    - Eliminates rebuilding kernel modules for all kernel updates, and allows kernel modules built against older versions of the kernel to be more easily supported on updated kernels
- Secure Digital High Capacity Support
    - Available on Performance CompactRIO and NI System on Module devices with an SD Card slot interface
- WebDAV File Browser
    - Enables secure, browser based authenticated access to the filesystem on all NI embedded devices

### Changed
- OpenEmbedded Update on ARM targets
    - Applies to Zynq based devices: cRIO-9068, myRIO, etc.
    - New user mode libraries. Users will no longer run into conflicts about improper versions of core libraries not being present when trying to load other applications/packages from the Linux community onto their target. Notably, the GCC package was updated as a part of this feature to GCC 4.7
- Update to udev from mdev
    - Updated the device manager from mdev to udev. udev enables dynamic device enumeration and configuration which allows for easier device management and hotplug functionality

### Security
- Released with the newest OpenSSL package (among other packages) to avoid Heartbleed and other vulnerabilities altogether. No NI products were ever affected by Heartbleed as a result.

## 1.0

- Initial release of NI Linux Real-Time
    - Hardware Support for ARM devices: (Zynq based CompactRIO-9068 and myRIO targets)
