# NI Linux RT Contribution Guide

Thanks for taking an interest in contributing to the project!


## Project Information

The canonical upstream for this project is: [github.com/ni/nilrt](https://github.comn/ni/nilrt). Please use that repository for bug reports and pull requests.

The OE-layers used by the project are also available under the [github.com/ni](https://github.com/ni/) group. The [meta-nilrt](https://github.com/ni/meta-nilrt) layer is owned by NI, and the information in this CONTRIBUTING file applies to it as well.

Current Project Maintainers:
* Alex Stewart <[alex.stewart@ni.com](mailto:alex.stewart@ni.com)> [[Github](https://github.com/amstewart)]
* Shruthi Ravichandran <[shruthi.ravichandran@ni.com](mailto:shruthi.ravichandran@ni.com)> [[Github](https://github.com/shruthi-ravi)]
* The NI RTOS Team <[dsw.rtos@ni.com](mailto:dsw.rtos@ni.com)>


### Branches

To support rolling product development, NILRT frequently maintains multiple mainline development branches, each rebased upon a different OE upstream stable release. The mainline branch refs are namespaced like `nilrt/master/${oe_stable}`. The mainline branches are generally open to contribution until they reach the end of their life.

Status | NI Release | NILRT Version | Branch Ref
-------|------------|---------------|-----------
Open | 21.X  | 9.X | [nilrt/master/dunfell](https://github.com/ni/nilrt/tree/nilrt/master/dunfell)
Open | 20.X  | 8.X | [nilrt/master/sumo](https://github.com/ni/nilrt/tree/nilrt/master/sumo)

NILRT follows a mainline-branch model. Near a release, the project maintainers create a product branch for stable production builds. The branches are named `nilrt/${ni_release}/${oe_stable}` like `nilrt/20.6/sumo`, and are only open to necessary bug fixes and security backports relevant to the product release.


### Contributing Patches

Patches to the [nilrt](https://github.com/ni/nilrt/pulls) repo and [meta-nilrt](https://github.com/ni/meta-nilrt/pulls) OE layer repos should be submitted as Github PRs. The simplest method is to fork the NI repo using your Github account, upload your patchset as a branch to your personal repo, then open a Pull Request using the github interface.

Github PRs should be preferred in all cases. If it is not possible for you to use Github, you can submit a patchset privately by emailing it to the project maintainers enumerated above (and cc'ing the NI RTOS team).


### Reporting Issues

**Issues with the NI LinuxRT distribution source** should be filed using the [Issues tracker](https://github.com/ni/nilrt/issues) on Github. If you know that the bug is isolated to a particular OE layer, you might use the Issues tracker for that repository instead.

**Runtime issues and help** using your Linux RT distribution are best filed on the [NI RT discussion forum](https://forums.ni.com/t5/NI-Linux-Real-Time-Discussions/bd-p/7111?profile.language=en), which is regularly monitored by NI support engineers and knowledgeable members of the community.

**Security concerns** are best filed with the [NI security team](https://www.ni.com/en-us/support/security.html) via the group email: <[security@ni.com](mailto:security@ni.com)>.


## NI OE Styleguide

### Where to make recipe changes?

OE recipe metadata is distributed across bitbake layers within the project, and it is generally important to the health of the distribution that recipe changes are made in the appropriate layers.

If your recipe changes are appropriate for the OpenEmbedded community as a whole, they should be submitted to the appropriate community-layer upstream first. Once accepted by upstream, they should be cherry-picked back into the NI-owned fork of the layer.

If your recipe changes are specific to NI LinuxRT, they should be made in the `meta-nilrt` layer.

Keep in mind that it might be most-correct to split your patchset changes across layers, if part of the changes are OE-generic and part are NILRT-specific.

### .patch Files

[Example of a good .patch file commit.](https://github.com/ni/meta-nilrt/pull/50/commits/73b046c57d73e188a3bf4adbf0965aa9312ebe08)

`.patch` files should include the original author's commit message and meta information at their top. Information about the OE context (like why the `.patch` file is needed for the recipe) should be added after the original author's commit.

At a minimum, you should add an additional message trailer declaring the upstream status of the .patch file at the time of your OE commit. These status lines are crucial to helping the project maintainers properly upgrade and rebase recipes. Common status lines are:

* `Upstream-Status: Inappropriate [$rationale]` ([ex](https://github.com/ni/meta-nilrt/blob/nilrt/master/sumo/recipes-support/curl/curl/0005-Add-nicurl-wrapper-functions.patch)) For when the `.patch` change is specific to NI LinuxRT and would not be desired (or has been rejected) by upstream.
* `Upstream-Status: Not Submitted [$rationale]` ([ex](https://github.com/ni/meta-nilrt/blob/nilrt/master/sumo/recipes-gnome/florence/files/0004-Add-option-for-automatic-bring-to-top.patch)) For when the `.patch` file is being included in NILRT before being submitted to its upstream project. This should only occur if the `.patch` is needed for an immediate NILRT release and there is no time to get it reviewed upstream beforehand. Or if - as in the case of the example - the upstream mailing list is dead.
* `Upstream-Status: Submitted [$upstream_mailing_list_link]` ([ex](https://github.com/ni/meta-nilrt/blob/1e6453ebca8735de96eaaf3bc931d22998c8dfb3/recipes-support/curl/curl/0014-Fixup-lib1529-test.patch)) For when the `.patch` has been submitted to the upstream project's mailing list, but needs to be pulled into NILRT prior to final upstream approval.
* `Upstream-Status: Accepted [$upstream_mailing_list_link]` ([ex](https://github.com/ni/meta-nilrt/blob/904bd00bf24d8fe61d3a13b8ece368c9741a73fc/recipes-devtools/opkg/files/0002-libopkg-clear-curl-properties-on-download-error-to-p.patch#L36)) For when the `.patch` has been approved and pulled by the upstream project.


#### .patch file names

When bitbake applies `.patch` files to a recipe, it copies all `.patch` files into the recipe's workspace, then applies them in alphanumeric-order. In your PR, be mindful of how your `.patch` file is ordered versus the other files in the recipe. Keep in mind that some `.patch` files might come from other layers.
