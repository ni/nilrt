# Changelog

This changelog consolidates changes for the [nilrt](https://github.com/ni/nilrt) repo, [meta-nilrt](https://github.com/ni/meta-nilrt) OE layer, and NI's branch of the [linux](https://github.com/ni/linux) kernel. Other OE layer changes are tracked in their respective changelogs.

The NI Linux Real-Time project uses a mainline branching model with product branches for stable releases.

This changelog attempts to conform to the changelog spec on [keepachangelog.org](https://keepachangelog.com/en/1.0.0/).

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
