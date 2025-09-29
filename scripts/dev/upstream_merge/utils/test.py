"""Functions for testing built images on a VM via SSH."""

import os
import time

from .shell_commands import execute_and_stream_cmd_output

BUILD_DIR = "/build/tmp-glibc/deploy/images/x64/"
SAFEMODE_IMAGE = "nilrt-safemode-rootfs-x64.tar.gz"
RUNMODE_IMAGE = "nilrt-base-system-image-x64.tar"


def install_and_test_image(ssh_connection):
    """
    perform the following steps to test the built images on the target machine:
    1. set safemode
    2. reboot
    3. format the machine, enable sshd, and reboot
    4. current os version
    5. install safemode image
    6. verify os version
    7. install runmode image
    8. verify os version
    """
    print("\nStarting OS test...")

    # Step 1: Set safemode
    print("Setting safemode...")
    result = execute_and_stream_cmd_output(
        f'ssh -o StrictHostKeyChecking=no {ssh_connection} "/etc/init.d/nisetbootmode force-safemode"'
    )
    if result[0] != 0:
        return result

    # Step 2: Reboot
    print("Rebooting after setting safemode...")
    reboot = reboot_machine(ssh_connection)
    if reboot[0] != 0:
        return reboot
    time.sleep(90)  # Wait for reboot

    # Step 3: Format, enable sshd, and reboot
    result = format_and_enable_ssh(ssh_connection)
    if result[0] != 0:
        return result

    # Step 4: Get current OS version
    print("Verifying current OS version...")
    current_os = verify_os_version(ssh_connection)
    if current_os[0] != 0:
        return current_os
    print(f"Current OS version:\n{current_os[1]}")

    # Step 5: Install safemode image
    print("Installing safemode image...")
    safemode_install = test_safemode_installation(ssh_connection)
    if safemode_install[0] != 0:
        return safemode_install

    # Step 6: Verify OS version after safemode install
    print("Verifying OS version after safemode installation...")
    os_after_safemode = verify_os_version(ssh_connection)
    if os_after_safemode[0] != 0:
        return os_after_safemode
    print(f"OS version after safemode installation:\n{os_after_safemode[1]}")

    # Step 7: Install runmode image
    print("Installing runmode image...")
    runmode_install = test_runmode_installation(ssh_connection)
    if runmode_install[0] != 0:
        return runmode_install

    # Step 8: Verify OS version after runmode install
    print("Verifying OS version after runmode installation...")
    os_after_runmode = verify_os_version(ssh_connection)
    if os_after_runmode[0] != 0:
        return os_after_runmode
    print(f"OS version after runmode installation:\n{os_after_runmode[1]}")

    return os_after_runmode


def format_and_enable_ssh(ssh_connection):
    """
    Format the machine, enable sshd, and reboot.
    """
    print("Formatting the machine, enabling sshd, and rebooting...")
    result = execute_and_stream_cmd_output(
        f"ssh -o StrictHostKeyChecking=no {ssh_connection} \"nisystemformat -f -t ext4 -n all && "
        "sed -i 's/^sshd.enabled=.*/sshd.enabled=True/' "
        "/etc/natinst/share/ni-rt.ini && reboot\""
    )
    if result[0] != 0:
        return result
    time.sleep(90)  # Wait for reboot

    return (0, None)


def test_safemode_installation(ssh_connection):
    """
    Copy, extract, and install the safemode image on the target machine.
    """
    current_directory = os.getcwd()
    copy = execute_and_stream_cmd_output(
        f"scp {current_directory}{BUILD_DIR}{SAFEMODE_IMAGE} "
        f"{ssh_connection}:/home/admin"
    )
    if copy[0] != 0:
        return copy

    extract_and_install = extract_and_install_safemode_image(ssh_connection)
    if extract_and_install[0] != 0:
        return extract_and_install

    reboot = reboot_machine(ssh_connection)
    if reboot[0] != 0:
        return reboot

    time.sleep(90)  # Wait for the machine to reboot

    return (0, None)


def test_runmode_installation(ssh_connection):
    """
    Copy, extract, and install the runmode image on the target machine.
    """
    current_directory = os.getcwd()
    copy = execute_and_stream_cmd_output(
        f"scp -o StrictHostKeyChecking=no {current_directory}{BUILD_DIR}{RUNMODE_IMAGE} "
        f"{ssh_connection}:/mnt/userfs"
    )
    if copy[0] != 0:
        return copy

    extract_and_install = extract_and_install_runmode_image(ssh_connection)
    if extract_and_install[0] != 0:
        return extract_and_install

    reboot = reboot_machine(ssh_connection)
    if reboot[0] != 0:
        return reboot

    time.sleep(300)  # Wait for the machine to reboot

    return (0, None)


def extract_and_install_safemode_image(ssh_connection):
    """
    Extract and install the safemode image on the target machine.
    """
    print("Extracting safemode image on target machine...")
    return execute_and_stream_cmd_output(
        f'ssh -o StrictHostKeyChecking=no {ssh_connection} "tar xf {SAFEMODE_IMAGE} -C /boot/.safe/"'
    )


def extract_and_install_runmode_image(ssh_connection):
    """
    Extract and install the runmode image on the target machine.
    """
    print("Extracting runmode image on target machine...")

    # Change to /mnt/userfs and extract the tar
    first_cmd = execute_and_stream_cmd_output(
        f'ssh -o StrictHostKeyChecking=no {ssh_connection} "cd /mnt/userfs && tar xf {RUNMODE_IMAGE}"'
    )
    if first_cmd[0] != 0:
        return first_cmd

    # Extract data.tar.gz and run postinst
    second_cmd = execute_and_stream_cmd_output(
        f'ssh -o StrictHostKeyChecking=no {ssh_connection} "cd /mnt/userfs && tar xf data.tar.gz -C '
        f'/mnt/userfs && ./postinst"'
    )
    if second_cmd[0] != 0:
        return second_cmd

    # Remove the tar, data.tar.gz, and postinst files
    cleanup_cmd = execute_and_stream_cmd_output(
        f'ssh -o StrictHostKeyChecking=no {ssh_connection} "cd /mnt/userfs && rm -f {RUNMODE_IMAGE} '
        f'data.tar.gz postinst"'
    )
    if cleanup_cmd[0] != 0:
        return cleanup_cmd

    return (0, None)


def reboot_machine(ssh_connection):
    """
    Reboot the target machine.
    """
    print("Rebooting the machine...")
    return execute_and_stream_cmd_output(f'ssh -o StrictHostKeyChecking=no {ssh_connection} "reboot"')


def verify_os_version(ssh_connection):
    """
    Verify the OS version on the target machine.
    """
    print("Verifying OS version...")
    return execute_and_stream_cmd_output(
        f'ssh -o StrictHostKeyChecking=no {ssh_connection} "cat /etc/os-release"'
    )


if __name__ == "__main__":
    # Example usage:
    SSH_CONNECTION = ""
    status_code, message = install_and_test_image(SSH_CONNECTION)
    if status_code == 0:
        print("\n OS test completed successfully.")
    else:
        print(
            f"\n OS test failed with status code {status_code}. "
            f"Error: {message}"
        )
