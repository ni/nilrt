#!/usr/bin/env python3

"""
    This test validates ssl certicates for the last 4 releases
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import zipfile
import pexpect

MINIMUM_VERSION_CG = 7.0
MINIMUM_VERSION_NG = "cobra"
NG_VERSIONS = ["cobra", "lynx"]

def check_version(flavor, version):
    """
        Check if provided version is supported for this test
        based on flavor.
    """
    return (flavor == "cg" and re.compile(r"^[1-9][0-9]*(\.[0]+)?$").match(version) \
            and float(version) >= MINIMUM_VERSION_CG) or \
           (flavor == "ng" and version in NG_VERSIONS)

EXAMPLE = '''example:

 {0} $BALTIC_MNT/penguinExports/nilinux/os-common/export cg 7.0
 {0} $BALTIC_MNT/penguinExports/nilinux/nilrt-oe ng lynx'''.format(sys.argv[0])

PARSER = argparse.ArgumentParser(description=__doc__,
                                 epilog=EXAMPLE,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
PARSER.add_argument('image_path', help='Image export path.')
PARSER.add_argument('image_flavour', choices=['cg', 'ng'], help='Image flavour.')
PARSER.add_argument('image_version', help='''Image version to be tested.
                                              For cg, version should be a point release >= 7.0 and
                                              for ng, version should be {}.'''
                    .format('/'.join(NG_VERSIONS)))
ARGS = PARSER.parse_args(sys.argv[1:])

if not check_version(ARGS.image_flavour, ARGS.image_version):
    PARSER.print_help()
    exit(1)

def get_latest(export, version=""):
    """
    Get latest export for a given export path and version (Optional)
    """
    return max(glob.glob(os.path.join("{}/{}".format(export, version), '*')), key=os.path.getctime)

def test_cmd(child_image, command, extra_expectations=None):
    """
    Test a command on a given image
    """
    child_image.sendline(command)
    if extra_expectations:
        for expectation in extra_expectations:
            child_image.expect(expectation)
    child_image.expect("# ")
    child_image.sendline("echo $?")
    child_image.expect("0\r")

def login(child_image, flavor):
    """
    Login into the image
    """
    child_image.expect("NI Linux Real-Time")
    child_image.expect("NI.* login:")
    if flavor == "cg":
        child_image.sendline("admin")
        child_image.expect("Password: ")
        child_image.sendline()
    else:
        child_image.sendline("root")
    child_image.expect("# ")

def verify_all_ssl_certificates(child_image, index):
    """
        Verifing expiration date for root certificate.
        This should not expire in the next (4 - index) years.
    """
    child_image.sendline("echo -n | openssl s_client -showcerts -connect download.ni.com:443 \
< /dev/null | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > allcerts")
    child_image.expect("DONE")
    child_image.expect("# ")
    child_image.sendline("awk 'BEGIN{c=0} {print $0 > \"certificate\"c\".perm\"; if \
($0 == \"-----END CERTIFICATE-----\") c++}' allcerts")
    child_image.expect("# ")
    test_cmd(child_image, "openssl x509 -checkend {} -noout -in $(ls certificate*.perm \
| tail -1)".format(31557600 * (4 - index)))

def get_old_version(flavor, version, index):
    """
        Get an old version based on flavor, current version and index
    """
    if flavor == "cg":
        old_version = float(version) - index
        if old_version >= MINIMUM_VERSION_CG:
            return old_version
    else:
        old_version = NG_VERSIONS.index(version) - index
        if old_version >= 0:
            return NG_VERSIONS[old_version]
    return None

def get_image_path(image_path, flavor, version):
    """
        Get image path based on flavor and version
    """
    return "{}/targets/linuxU/x64/gcc-4.7-oe/release/nilrt-vm-cg-x64-qemu.zip" \
           .format(get_latest(image_path, version)) if flavor == "cg" else \
        "{}/images/NILinuxRT-x64/nilrt-vm-x64-qemu.zip" \
        .format(get_latest(get_latest("{}/{}/export".format(image_path, version))))

TEST_TIMEOUT = 600 # seconds
FLAVOR = ARGS.image_flavour
VERSION = ARGS.image_version

for i in range(0, 4):
    new_version = get_old_version(FLAVOR, VERSION, i)

    if new_version is None:
        break

    IMAGE_PATH = get_image_path(ARGS.image_path, FLAVOR, new_version)

    print("Fetching VM image from: {}".format(IMAGE_PATH))
    if os.path.exists("nilrt-vm-x64-qemu"):
        shutil.rmtree("nilrt-vm-x64-qemu")
    zf = zipfile.ZipFile(IMAGE_PATH)
    zf.extractall("nilrt-vm-x64-qemu")
    os.chdir("nilrt-vm-x64-qemu")

    print("Booting os image version {}".format(new_version))
    ENABLE_KVM = subprocess.check_output(["""id | grep -q kvm && echo -n '-enable-kvm -cpu kvm64' \
    || echo -n ''"""], shell=True)
    CHILD = pexpect.spawn("""qemu-system-x86_64 {} -nographic -m 1024 -hda {} -netdev user,id=u1
    -device e1000,netdev=u1""".format(str(ENABLE_KVM, "utf-8"),
                                      "nilrt-vm{0}-x64-qemu/nilrt-vm{0}-x64.qcow2" \
                                      .format("-cg" if FLAVOR == "cg" else "")),\
                                    timeout=TEST_TIMEOUT, encoding="utf-8")
    login(CHILD, FLAVOR)

    print("Verifying version {} (flavor: {}) ... ".format(new_version, FLAVOR))

    print("Verifying ssl certificates with opkg")
    test_cmd(CHILD, "opkg update > /dev/null 2>&1")
    test_cmd(CHILD, "opkg install ntpdate > /dev/null 2>&1")
    test_cmd(CHILD, "ntpdate time.nist.gov > /dev/null 2>&1")
    print("Verifying with wget")
    test_cmd(CHILD, "wget https://download.ni.com/ni-linux-rt/feeds/")
    print("Verifying with curl")
    test_cmd(CHILD, "curl https://download.ni.com/ni-linux-rt/feeds/")
    print("Verifying with openssl")
    test_cmd(CHILD, "openssl s_client -connect download.ni.com:443", ["closed"])
    print("Verifying expiration date of root certificate")
    verify_all_ssl_certificates(CHILD, i)

    print("Version {} (flavor: {}): OK".format(new_version, FLAVOR))
    CHILD.sendline("poweroff")
print("All tests passed")
