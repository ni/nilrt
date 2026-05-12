"""
Rebuild NI out-of-tree drivers using DKMS.
This file is intentionally isolated from kernel build/install logic.
"""

def install_sshfs_fuse(config, run_cmd):
    ssh_target = config.ssh_target

    print("[REBUILD][STEP 0] Install sshfs-fuse and load fuse")

    # opkg update (SSH drop expected)
    rc, out = run_cmd(f"ssh {ssh_target} 'opkg update || true'")
    print(out)

    # opkg install
    rc, out = run_cmd(
        f"ssh {ssh_target} 'opkg install sshfs-fuse || true'"
    )
    print(out)

    # VERIFY sshfs exists
    rc, out = run_cmd(f"ssh {ssh_target} 'which sshfs'")
    print(out)
    if rc != 0:
        print("[REBUILD][ERROR] sshfs not installed")
        return 1

    # load fuse
    rc, out = run_cmd(f"ssh {ssh_target} 'modprobe fuse'")
    print(out)
    if rc != 0:
        print("[REBUILD][ERROR] modprobe fuse failed")
        return 1

    print("[REBUILD][OK] sshfs-fuse ready")
    return 0


def mount_kernel_source(config, run_cmd):
    ssh_target = config.ssh_target
    kernel_src_dir = config.kernel_src_dir
    host_user = config.build_host_user
    host_ip = config.build_host_ip

    print("[REBUILD][STEP 1] Mount kernel source via SSHFS")

    run_cmd(f'ssh {ssh_target} "mkdir -p /usr/src/linux"')
    run_cmd(
        f'ssh {ssh_target}'
        f'"mount | grep /usr/src/linux && umount /usr/src/linux || true"'
    )

    rc, out = run_cmd(
        f'ssh {ssh_target} '
        f'"sshfs {host_user}@{host_ip}:{kernel_src_dir} /usr/src/linux"'
    )
    print(out)

    rc, out = run_cmd(
        f'ssh {ssh_target} "test -f /usr/src/linux/Makefile && echo OK"'
    )
    print(out)

    if rc != 0:
        print("[REBUILD][ERROR] Kernel source not visible at /usr/src/linux")
        return 1

    print("[REBUILD][OK] Kernel source mounted via SSHFS")
    return 0


def fix_symlinks(config, run_cmd):
    ssh_target = config.ssh_target

    print("[REBUILD][STEP 2] Fix build/source symlinks")

    rc, out = run_cmd(
        f"ssh {ssh_target} "
        "'cd /lib/modules/$(uname -r) && "
        "rm -f build source && "
        "ln -s /usr/src/linux source && "
        "ln -s source build'"
    )
    print(out)

    if rc != 0:
        print("[REBUILD][ERROR] Failed to fix build/source symlinks")
        return 1

    # Optional but good verification
    rc, out = run_cmd(
        f"ssh {ssh_target} "
        "'ls -l /lib/modules/$(uname -r)/build "
        "/lib/modules/$(uname -r)/source'"
    )
    print(out)

    print("[REBUILD][OK] build and source symlinks fixed")
    return 0


def prepare_headers(config, run_cmd):
    ssh_target = config.ssh_target

    print("[REBUILD][STEP 3] Prepare kernel headers")

    rc, out = run_cmd(
        f"ssh {ssh_target} "
        "'cd /lib/modules/$(uname -r)/build && "
        "make prepare && make modules_prepare'"
    )
    print(out)

    if rc != 0:
        print("[REBUILD][ERROR] Kernel header preparation failed")
        return 1

    print("[REBUILD][OK] Kernel headers prepared")
    return 0


def dkms_autoinstall(config, run_cmd):
    ssh_target = config.ssh_target

    print("[REBUILD][STEP 4] DKMS autoinstall")

    rc, out = run_cmd(f"ssh {ssh_target} 'dkms autoinstall'")
    print(out)

    if rc != 0:
        print("[REBUILD][ERROR] DKMS autoinstall failed")
        return 1

    rc, out = run_cmd(f"ssh {ssh_target} 'dkms status'")
    print(out)

    print("[REBUILD][OK] DKMS rebuild complete")
    return 0
