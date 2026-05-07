#!/usr/bin/env python3
import os
import sys
import re
import argparse
import time
from log_and_email_utils import setup_logging, write_log_and_send_email
from utils.git_commands import (
    git_fetch,
    git_remote,
    git_merge,
    git_reset,
    git_clean,
    git_merge_abort,
    git_tag,
    git_status,
    git_clone,
    git_checkout,
)
from utils.git_repo import GitRepo
from json_config import JsonConfig
from toolchain_build import copy_toolchain_from_nirvana
from toolchain_build import prepare_toolchain_environment
from rebuild_drivers import step0_install_sshfs_fuse
from rebuild_drivers import step1_mount_kernel_source
from rebuild_drivers import step2_fix_symlinks
from rebuild_drivers import step3_prepare_headers
from rebuild_drivers import step4_dkms_autoinstall
from utils.push_branch_and_create_pr import push_branch_and_create_pr
# --------------------
# Import shared utils
# --------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
dev_dir = os.path.dirname(script_dir)
upstream_merge_dir = os.path.join(dev_dir, "upstream_merge")
sys.path.append(upstream_merge_dir)

REPO_URL = "https://github.com/ni/linux.git"
STABLE_RT_REMOTE = (
    "https://git.kernel.org/pub/scm/linux/kernel/git/rt/linux-stable-rt.git"
)


# --------------------
# Kernel build config (x86_64)
# --------------------
KERNEL_DEFCONFIG = "nati_x86_64_defconfig"


config = None


# --------------------
# CLI
# --------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Stable-RT merge automation")
    parser.add_argument(
        "-c",
        "--config",
        default="scripts/dev/upstream_merge/automation_conf.json"
    )
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--work-dir", default=None)
    parser.add_argument(
        "--skip-push-and-pr",
        action="store_true",
        help="Skip pushing branch and creating PR"
    )
    return parser.parse_args()


def wait_for_ssh(ssh_target, ssh_opts="", timeout=120):
    print(f"[INFO] Waiting for SSH on {ssh_target}...")

    for _ in range(timeout // 5):
        ret = os.system(
            f'ssh {ssh_opts} {ssh_target} "echo ok" > /dev/null 2>&1'
        )
        if ret == 0:
            print("[INFO] SSH is available on target")
            return 0
        time.sleep(5)

    return 1


def run_cmd(cmd):
    """
    Run a shell command and return (rc, output).
    rc = 0 on success, 1 on failure.
    """
    stream = os.popen(cmd + " 2>&1")
    output = stream.read().strip()
    rc = stream.close()
    if rc is not None:
        return 1, output
    return 0, output


# --------------------
# Kernel repo handling
# --------------------
def clone_kernel_repository():
    print("[INFO] Cloning kernel repository")

    repo = os.path.abspath(config.kernel_src_dir)
    config.kernel_src_dir = repo

    os.makedirs(os.path.dirname(repo), exist_ok=True)
    git_clone(REPO_URL, repo)


def regenerate_defconfig(kernel_src_dir):
    """
    US-4:
    Regenerate nati_x86_64_defconfig and create a commit if it changes.
    Returns True if a commit was created, False otherwise.
    """
    print("[US4] Regenerating nati_x86_64_defconfig")

    original_cwd = os.getcwd()
    os.chdir(kernel_src_dir)

    cmds = [
        "make mrproper",
        "make nati_x86_64_defconfig",
        "make savedefconfig",
        "mv defconfig arch/x86/configs/nati_x86_64_defconfig",
    ]

    for cmd in cmds:
        rc = os.system(cmd)
        if rc != 0:
            os.chdir(original_cwd)
            raise RuntimeError(f"[US4][ERROR] Command failed: {cmd}")

    # Check for diff
    diff_rc = os.system(
        "git diff --quiet arch/x86/configs/nati_x86_64_defconfig"
    )

    if diff_rc == 0:
        print("[US4] Defconfig unchanged")
        os.chdir(original_cwd)
        return False

    print("[US4] Defconfig changed, creating commit")

    rc = os.system("git add arch/x86/configs/nati_x86_64_defconfig")
    if rc != 0:
        os.chdir(original_cwd)
        raise RuntimeError("[US4][ERROR] git add failed")

    rc = os.system(
        'git commit -s -m '
        '"nati_x86_64_defconfig: regenerate; no functional changes"'
    )
    if rc != 0:
        os.chdir(original_cwd)
        raise RuntimeError("[US4][ERROR] git commit failed")

    os.chdir(original_cwd)
    return True

# --------------------
# RT Merge
# --------------------


def run_upstream_merge_script(args):
    original_cwd = os.getcwd()
    print("[INFO] Running upstream RT merge")

    clone_kernel_repository()

    kernel_repo = GitRepo(
        local_repo=config.kernel_src_dir,
        upstream_repo_url=REPO_URL,
        upstream_branch=config.target_branch,
    )

    os.chdir(config.kernel_src_dir)

    try:
        git_merge_abort()
    except Exception:
        pass

    git_reset(hard=True)
    git_clean(force=True, directories=True, ignored_files=True)

    git_fetch("origin")
    git_checkout(config.target_branch, create=True, force_checkout=True)
    git_reset(hard=True, target=f"origin/{config.target_branch}")

    _, remotes = git_remote()
    if "stable-rt" not in remotes:
        git_remote("stable-rt", STABLE_RT_REMOTE)

    git_fetch("stable-rt", "--tags")

    kernel_version = config.target_branch.split("/")[-1]
    _, tags = git_tag(list_pattern=f"v{kernel_version}.*-rt*")

    clean_tags = [
        t
        for t in tags.splitlines()
        if re.match(rf"^v{kernel_version}\.\d+-rt\d+$", t)
    ]

    if not clean_tags:
        raise RuntimeError("No stable-RT tags found")

    latest_tag = sorted(
        clean_tags, key=lambda t: list(map(int, re.findall(r"\d+", t)))
    )[-1]

    print(f"[INFO] Latest RT tag: {latest_tag}")

    result = git_merge(
        latest_tag, signoff=True, message=f"Merge latest upstream {latest_tag}"
    )

    # --------------------
    # Failure case
    # --------------------
    if result[0] != 0:
        _, status_out = git_status()

        merge_details = (
            status_out
            if ("both modified" in status_out or "unmerged" in status_out)
            else "Merge failed before conflicts were created."
        )

        merge_report = {
            kernel_repo: (1, merge_details),
            "Build and Test": (1, "Skipped because merge failed"),
        }

        os.chdir(original_cwd)
        write_log_and_send_email(
            email_from=config.email_from,
            email_to=config.email_to,
            merge_report=merge_report,
            email_log_level=0,
            skip_push_and_pr=True,
        )
        return

    # --------------------
    # Success case
    # --------------------
    print("[INFO] RT merge successful")

    # --------------------
    # Copy toolchain from Nirvana
    # --------------------
    build_root = os.path.dirname(config.kernel_src_dir)
    tc_copy_status, tc_copy_msg = copy_toolchain_from_nirvana(build_root)
    if tc_copy_status != 0:
        merge_report = {
            kernel_repo: (
                1,
                f"RT tag {latest_tag} merged successfully.\n"
                f"Branch: {config.target_branch}",
            ),
            "Build and Test": (1, tc_copy_msg),
        }

        os.chdir(original_cwd)
        write_log_and_send_email(
            email_from=config.email_from,
            email_to=config.email_to,
            merge_report=merge_report,
            email_log_level=0,
            skip_push_and_pr=True,
        )
        return
    # --------------------
    # Prepare toolchain environment
    # --------------------
    tc_status, tc_msg = prepare_toolchain_environment(build_root)
    if tc_status != 0:
        merge_report = {
            kernel_repo: (
                1,
                f"RT tag {latest_tag} merged successfully.\n"
                f"Branch: {config.target_branch}",
            ),
            "Build and Test": (1, tc_msg),
        }

        os.chdir(original_cwd)
        write_log_and_send_email(
            email_from=config.email_from,
            email_to=config.email_to,
            merge_report=merge_report,
            email_log_level=0,
            skip_push_and_pr=True,
        )
        return

    defconfig_changed = regenerate_defconfig(config.kernel_src_dir)
    if defconfig_changed:
        print("[US4] Defconfig regeneration commit created")
    # --------------------
    # Kernel build (x86_64)
    # --------------------
    build_status, build_msg = build_kernel_x86_64(config.kernel_src_dir)

    merge_report = {
        kernel_repo: (
            build_status,
            f"RT tag {latest_tag} merged successfully.\n"
            f"Branch: {config.target_branch}",
        ),
        "Build and Test": (build_status, build_msg),
    }

    # --------------------
    # Install kernel to target
    # --------------------
    install_status, install_msg = install_kernel_to_target(
        config.kernel_src_dir)
    merge_report = {
        kernel_repo: (
            install_status,
            f"RT tag {latest_tag} merged successfully.\n"
            f"Branch: {config.target_branch}",
        ),
        "Build and Test": (install_status, install_msg),
    }
    print("[INFO] Kernel install issued reboot request")

    time.sleep(20)

    print("[INFO] Waiting for target to come back after kernel reboot")
    if wait_for_ssh(config.ssh_target, timeout=300) != 0:
        print("[ERROR] Target did not come back after kernel reboot")
        return

    print("[INFO] Target is back online, starting rebuild drivers")

    # STEP 0: Ensure sshfs is available
    rc = step0_install_sshfs_fuse(config, run_cmd)
    if rc != 0:
        print("[ERROR] STEP 0 failed")
        return

    # STEP 1: Mount kernel source via SSHFS
    rc = step1_mount_kernel_source(config, run_cmd)
    if rc != 0:
        print("[ERROR] STEP 1 failed")
        return

    # STEP 2: Fix build/source symlinks
    rc = step2_fix_symlinks(config, run_cmd)
    if rc != 0:
        print("[ERROR] STEP 2 failed")
        return

    # STEP 3: Prepare kernel headers
    rc = step3_prepare_headers(config, run_cmd)
    if rc != 0:
        print("[ERROR] STEP 3 failed")
        return

    # STEP 4: DKMS rebuild
    rc = step4_dkms_autoinstall(config, run_cmd)
    if rc != 0:
        print("[ERROR] STEP 4 failed")
        return
    # PR creation (FINAL STEP ONLY) ----
    if not args.skip_push_and_pr:
        pr_title = f"[{config.work_item_id}] Merge RT {latest_tag}"

        pr_description = (
            f"AB#{config.work_item_id}\n\n"
            f"RT tag merged: {latest_tag}\n"
            f"Defconfig regenerated: "
            f"{'Yes' if defconfig_changed else 'No'}\n"
            f"Kernel build: Success\n"
            f"Driver rebuild: Success\n"
        )

        git_obj = GitRepo(
            local_repo=config.kernel_src_dir,
            local_base_branch=config.pr_target_branch,
        )

        status, msg = push_branch_and_create_pr(
            git_obj,
            branch_name=config.target_branch,
            username=config.pr_username,
            pr_title=pr_title,
            pr_description=pr_description,
        )

        if status != 0:
            raise RuntimeError(f"Failed to create PR: {msg}")

        print("[INFO] Branch pushed and PR created successfully")
    os.chdir(original_cwd)
    write_log_and_send_email(
        email_from=config.email_from,
        email_to=config.email_to,
        merge_report=merge_report,
        email_log_level=0,
        skip_push_and_pr=args.skip_push_and_pr,
    )
    return


def build_kernel_x86_64(kernel_src_dir):
    print("[INFO] Starting x86_64 kernel build")

    if not os.path.isdir(kernel_src_dir):
        return 1, f"Kernel source directory not found: {kernel_src_dir}"

    # kernel_src_dir = <work-dir>/nilrt-kernel-build/linux
    build_root = os.path.dirname(kernel_src_dir)

    # Read from config
    jobs = getattr(config, "kernel_build_jobs", os.cpu_count() or 8)
    temp_modules_rel = getattr(config, "temp_modules_dir", "tmp-glibc/modules")

    temp_modules_dir = os.path.join(build_root, temp_modules_rel)
    os.makedirs(temp_modules_dir, exist_ok=True)

    os.chdir(kernel_src_dir)

    # Ensure ARCH is correct
    os.environ["ARCH"] = "x86_64"

    # Step 1: Configure kernel
    ret = os.system(f"make {KERNEL_DEFCONFIG}")
    if ret != 0:
        return 1, "Kernel defconfig failed"

    # Step 2: Build kernel and modules
    ret = os.system(f"make -j{jobs} bzImage modules")
    if ret != 0:
        return 1, "Kernel build failed (bzImage/modules)"

    # Step 3: Install modules to temp directory
    ret = os.system(
        f"make modules_install INSTALL_MOD_PATH={temp_modules_dir}")
    if ret != 0:
        return 1, "Kernel modules_install failed"

    return 0, (
        "Kernel built successfully (bzImage + modules)\n"
        f"Modules staged at: {temp_modules_dir}"
    )


def install_kernel_to_target(kernel_src_dir):
    """
    Install x86_64 kernel and modules to an NILRT target (cRIO).
    """

    ssh_target = config.ssh_target
    ssh_opts = getattr(config, "ssh_options", "")

    build_root = os.path.dirname(kernel_src_dir)

    bzimage = os.path.join(kernel_src_dir, "arch", "x86", "boot", "bzImage")

    if not os.path.isfile(bzimage):
        return 1, f"Kernel image not found: {bzimage}"

    # Get kernel version from build tree
    os.chdir(kernel_src_dir)
    kernel_version = os.popen("make -s kernelrelease").read().strip()

    print(f"[INFO] Installing kernel version: {kernel_version}")

    modules_root = os.path.join(
        build_root, "tmp-glibc", "modules", "lib", "modules", kernel_version
    )

    if not os.path.isdir(modules_root):
        return (
            1,
            f"Kernel modules for {kernel_version} "
            f"not found at {modules_root}",
        )

    # Backup existing kernel on target
    rc = os.system(
        f"ssh {ssh_opts} {ssh_target} "
        '"test ! -h /boot/runmode/bzImage && '
        'mv /boot/runmode/bzImage /boot/runmode/bzImage-$(uname -r) || true"'
    )
    if rc != 0:
        return 1, "Failed to backup existing kernel on target"

    # Copy kernel image
    rc = os.system(
        f"scp {ssh_opts} {bzimage} "
        f"{ssh_target}:/boot/runmode/bzImage-{kernel_version}"
    )
    if rc != 0:
        return 1, "FAILED to copy kernel bzImage to target (ABORTING)"

    # VERIFY kernel image exists on target
    rc = os.system(
        f"ssh {ssh_opts} {ssh_target} "
        f'"test -f /boot/runmode/bzImage-{kernel_version}"'
    )
    if rc != 0:
        return 1, "Kernel bzImage missing on target after copy (ABORTING)"

    # Update boot symlink
    rc = os.system(
        f"ssh {ssh_opts} {ssh_target} "
        f'"ln -sf bzImage-{kernel_version} /boot/runmode/bzImage"'
    )
    if rc != 0:
        return 1, "FAILED to update bzImage symlink (ABORTING)"

    # Copy kernel modules (versioned directory)
    rc = os.system(
        f"tar cz -C {modules_root} . | "
        f"ssh {ssh_opts} {ssh_target} "
        f'"mkdir -p /lib/modules/{kernel_version} && '
        f'tar xz -C /lib/modules/{kernel_version}"'
    )
    if rc != 0:
        return 1, "FAILED to copy kernel modules to target (ABORTING)"

    # VERIFY modules directory exists on target
    rc = os.system(
        f"ssh {ssh_opts} {ssh_target} "
        f'"test -d /lib/modules/{kernel_version}"'
    )
    if rc != 0:
        return 1, "Kernel modules missing on target after copy (ABORTING)"

    # CRITICAL: rebuild module dependency indexes
    rc = os.system(
        f"ssh {ssh_opts} {ssh_target} "
        f'"depmod -a {kernel_version}"'
    )
    if rc != 0:
        return 1, "depmod failed on target (ABORTING reboot)"

    # Reboot target ONLY after everything succeeded
    rc = os.system(f"ssh {ssh_opts} {ssh_target} reboot")
    if rc != 0:
        return 1, "FAILED to reboot target after install"

    return 0, (
        f"Kernel and modules installed successfully\n"
        f"Kernel version: {kernel_version}"
    )

# --------------------
# Main
# --------------------


def main():
    global config

    setup_logging()
    args = parse_args()

    config = JsonConfig(config_path=args.config, work_item_id=None)

    if args.work_dir:
        config.kernel_src_dir = os.path.join(
            args.work_dir, "nilrt-kernel-build", "linux"
        )

    print(f"[INFO] Branch: {config.target_branch}, " f"Arch: {config.arch}")

    if not args.skip_merge:
        run_upstream_merge_script(args)


if __name__ == "__main__":
    main()
