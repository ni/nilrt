"""Functions for testing built images on a VM."""

import os
import time

from .shell_commands import execute_and_stream_cmd_output

USERNAME = "admin"
TARGET = "NI-cRIO-903x-vm-27108694"
SSH_CONNECTION = USERNAME + "@" + TARGET
BUILD_DIR = "/build/tmp-glibc/deploy/images/x64/"
SAFEMODE_IMAGE = "nilrt-safemode-rootfs-x64.tar.gz"
RUNMODE_IMAGE = "nilrt-base-system-image-x64.tar"


def install_and_test_image(vm_name, snapshot_name):
    """
    Perform OS testing on the specified vm.
    Steps:
    1. Restore the vm to a specific snapshot.
    2. Start the vm.
    3. Copy, extract and install the safemode image.
    4. Copy, extract and install the runmode image.
    5. Verify the OS version.
    6. Power off the vm.
    """

    # Step 1: Restore the vm to the specified snapshot
    restore = restore_snapshot(vm_name, snapshot_name)
    if restore[0] != 0:
        return restore

    # Step 2: Start the vm
    start = start_vm(vm_name)
    if start[0] != 0:
        return start

    time.sleep(5)  # Wait for the vm to stabilize

    # Step 3: Copy, extract and install the safemode image
    install_safemode = test_safemode_installation()
    if install_safemode[0] != 0:
        return install_safemode

    # Step 4: Copy, extract and install the runmode image
    install_runmode = test_runmode_installation()
    if install_runmode[0] != 0:
        return install_runmode

    # Step 5: Verify the OS version
    os_version = verify_os_version()
    if os_version[0] != 0:
        return os_version

    # Step 6: Power off the vm
    poweroff = poweroff_vm(vm_name)
    if poweroff[0] != 0:
        return poweroff

    return os_version


def test_safemode_installation():
    """
    Copy, extract, and install the safemode image on
    the target machine using the provided SSH connection.
    """
    copy = copy_image(SAFEMODE_IMAGE)
    if copy[0] != 0:
        return copy

    extract_and_install = extract_and_install_safemode_image()
    if extract_and_install[0] != 0:
        return extract_and_install

    reboot = reboot_machine()
    if reboot[0] != 0:
        return reboot

    time.sleep(90)  # Wait for the machine to reboot

    return (0, None)


def test_runmode_installation():
    """
    Copy, extract, and install the runmode image on\
        the target machine using the provided SSH connection.
    """
    copy = copy_image(RUNMODE_IMAGE)
    if copy[0] != 0:
        return copy

    extract_and_install = extract_and_install_runmode_image()
    if extract_and_install[0] != 0:
        return extract_and_install

    reboot = reboot_machine()
    if reboot[0] != 0:
        return reboot

    time.sleep(150)  # Wait for the machine to reboot

    return (0, None)


def restore_snapshot(vm_name, snapshot_name):
    """
    Restore the vm to the specified snapshot.
    """
    print(f"Restoring to {snapshot_name} snapshot...")
    return execute_and_stream_cmd_output(
        f'VBoxManage snapshot "{vm_name}"'
        f' restore {snapshot_name}'
    )


def start_vm(vm_name):
    """
    Start the vm in headless mode.
    """
    print("Starting the vm...")
    return execute_and_stream_cmd_output(
        f'VBoxManage startvm "{vm_name}" --type headless'
    )


def copy_image(filename):
    """
    Copy the image to the target machine.
    """
    print("Copying image to target machine...")
    current_directory = os.getcwd()

    return execute_and_stream_cmd_output(
        f"scp {current_directory}{BUILD_DIR}{filename} \
        {SSH_CONNECTION}:/home/admin"
    )


def extract_and_install_safemode_image():
    """
    Extract and install the safemode image on the target machine
    using the provided SSH connection.
    """
    print("Extracting safemode image on target machine...")
    return execute_and_stream_cmd_output(
        f'ssh {SSH_CONNECTION} "tar xf '
        f'{SAFEMODE_IMAGE} -C /boot/.safe/"'
    )


def extract_and_install_runmode_image():
    """
    Extract and install the runmode image on the target machine.
    """
    print("Extracting runmode image on target machine...")
    first_cmd = execute_and_stream_cmd_output(
        f'ssh {SSH_CONNECTION} "tar xf '
        f'/home/admin/{RUNMODE_IMAGE}"'
    )
    if first_cmd[0] != 0:
        return first_cmd

    second_cmd = execute_and_stream_cmd_output(
        f'ssh {SSH_CONNECTION} "tar xf data.tar.gz -C '
        f'/mnt/userfs && ./postinst"'
    )
    if second_cmd[0] != 0:
        return second_cmd
    return (0, None)


def reboot_machine():
    """
    Reboot the target machine.
    """
    print("Rebooting the machine...")
    return execute_and_stream_cmd_output(
        f'ssh {SSH_CONNECTION} "reboot"'
    )


def verify_os_version():
    """
    Verify the OS version on the target machine.
    """
    print("Verifying OS version...")
    return execute_and_stream_cmd_output(
        f'ssh {SSH_CONNECTION} "cat /etc/os-release"'
    )


def poweroff_vm(vm_name):
    """
    Power off the vm.
    """
    print("Powering off the vm...")
    return execute_and_stream_cmd_output(
        f'VBoxManage controlvm "{vm_name}" poweroff'
    )


if __name__ == "__main__":
    status_code, message = install_and_test_image(
                            "NILRTAgain", "Clean_SSHEnabled"
                            )

    if status_code == 0:
        print("\n OS test completed successfully.")
    else:
        print(f"\n OS test failed with status code {status_code}."
              f"Error: {message}")
