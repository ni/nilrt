# NI Linux RT Contribution Guide

Thanks for taking an interest in contributing to the project!


## Project Information

The canonical upstream for this project is: [github.com/ni/nilrt](https://github.comn/ni/nilrt). Please use that repository for bug reports and pull requests.

The OE-layers used by the project are also available under the [github.com/ni](https://github.com/ni/) group. The [meta-nilrt](https://github.com/ni/meta-nilrt) layer is owned by NI, and the information in this CONTRIBUTING file applies to it as well.

Current Project Maintainers:
* Alex Stewart <[alex.stewart@ni.com](mailto:alex.stewart@ni.com)> [[Github](https://github.com/amstewart)]
* Shruthi Ravichandran <[shruthi.ravichandran@ni.com](mailto:shruthi.ravichandran@ni.com)> [[Github](https://github.com/shruthi-ravi)]
* The NI RTOS Team <[RTOS@ni.com](mailto:RTOS@ni.com)>


### Branches

To support rolling product development, NILRT frequently maintains multiple mainline development branches, each rebased upon a different OE upstream stable release. The mainline branch refs are namespaced like `nilrt/master/${oe_stable}`. The mainline branches are generally open to contribution until they reach the end of their life.

NILRT follows a mainline-branch model. Near a release, the project maintainers create a product branch for stable production builds. The branches are named `nilrt/${ni_release}/${oe_stable}` like `nilrt/20.6/sumo`, and are only open to necessary bug fixes and security backports relevant to the product release.


### Contributing Patches

Patches to the [nilrt](https://github.com/ni/nilrt/pulls) repo and [meta-nilrt](https://github.com/ni/meta-nilrt/pulls) OE layer repos should be submitted as Github PRs. The simplest method is to fork the NI repo using your Github account, upload your patchset as a branch to your personal repo, then open a Pull Request using the github interface.

Github PRs should be preferred in all cases. If it is not possible for you to use Github, you can submit a patchset privately by emailing it to the project maintainers enumerated above (and cc'ing the NI RTOS team).


### Reporting Issues

**Issues with the NI LinuxRT distribution source** should be filed using the [Issues tracker](https://github.com/ni/nilrt/issues) on Github. If you know that the bug is isolated to a particular OE layer, you might use the Issues tracker for that repository instead.

**Runtime issues and help** using your Linux RT distribution are best filed on the [NI RT discussion forum](https://forums.ni.com/t5/NI-Linux-Real-Time-Discussions/bd-p/7111?profile.language=en), which is regularly monitored by NI support engineers and knowledgeable members of the community.

**Security concerns** are best filed with the [NI security team](https://www.ni.com/en-us/support/security.html) via the group email: <[security@ni.com](mailto:security@ni.com)>.


## Developer Certificate of Origin (DCO)

   Developer's Certificate of Origin 1.1

   By making a contribution to this project, I certify that:

   (a) The contribution was created in whole or in part by me and I
       have the right to submit it under the open source license
       indicated in the file; or

   (b) The contribution is based upon previous work that, to the best
       of my knowledge, is covered under an appropriate open source
       license and I have the right under that license to submit that
       work with modifications, whether created in whole or in part
       by me, under the same open source license (unless I am
       permitted to submit under a different license), as indicated
       in the file; or

   (c) The contribution was provided directly to me by some other
       person who certified (a), (b) or (c) and I have not modified
       it.

   (d) I understand and agree that this project and the contribution
       are public and that a record of the contribution (including all
       personal information I submit with it, including my sign-off) is
       maintained indefinitely and may be redistributed consistent with
       this project or the open source license(s) involved.

(taken from [developercertificate.org](https://developercertificate.org/))

See [COPYING.MIT](https://github.com/ni/nilrt/blob/HEAD/COPYING.MIT)
for details about how nilrt is licensed.
