#!/usr/bin/env python3
"""Kernel build, merge (latest stable RT tag), deployment, and notification script.
Configuration via kernel_build_conf.json.
"""

import os
import sys
import tempfile
import shutil
import re
import argparse

script_dir = os.path.dirname(os.path.abspath(__file__))
upstream_merge_dir = os.path.join(script_dir, 'dev', 'upstream_merge')
sys.path.append(upstream_merge_dir)
from utils.shell_commands import run_command, execute_and_stream_cmd_output
from utils.git_commands import send_email, git_fetch, git_remote, git_checkout, git_merge, git_reset, git_clean, git_merge_abort, git_tag, git_status, git_diff
from utils.git_repo import GitRepo
from utils.toolchain import detect_or_build_cross_compile
from json_config import JsonConfig

config = None

def parse_args():
    parser = argparse.ArgumentParser(
        description="Automated kernel build, merge, and deployment script"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Path to configuration file",
        default="scripts/kernel_build_conf.json",
    )
    parser.add_argument("--skip-merge", action="store_true", help="Skip upstream merge step")
    parser.add_argument("--skip-packages", action="store_true", help="Skip package installation check")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--work-dir", type=str, help="Override working directory for kernel source", default=None)
    return parser.parse_args()

# === Utility Functions ===
def send_email_report(subject, body):
    tmpfile = tempfile.mktemp()
    with open(tmpfile, "w") as f:
        f.write(f"From: {config.email_from}\nTo: {config.email_to}\nSubject: {subject}\n\n{body}\n")
    try:
        send_email(to_address=config.email_to, subject=subject, file=tmpfile)
    finally:
        os.remove(tmpfile)

# Format merge conflict notification with limited file listing to reduce email size
def _format_conflict_email(latest_tag, conflicts, git_status_output, target_branch):
    conflict_list = [c for c in conflicts.splitlines() if c.strip()]
    max_files = 30
    shown_files = conflict_list[:max_files]
    truncated_note = "\n... (truncated)" if len(conflict_list) > max_files else ""
    # Keep only lines starting with 'U' (unmerged) from status, limit to 20
    status_lines = [l for l in git_status_output.splitlines() if l.strip().startswith('U')]
    status_lines = status_lines[:20]
    status_block = "\n\nGit status (unmerged entries only):\n" + "\n".join(status_lines) if status_lines else ""
    body = (
        f"Merge conflict while merging {latest_tag} into {target_branch}\n"
        f"Total conflicting files: {len(conflict_list)}\n"
        "Conflicting files:\n" + "\n".join(shown_files) + truncated_note + status_block
    )
    return body

# === Step 0: Check Required Packages ===
def check_required_packages():
    print("[INFO] Checking required Ubuntu packages...")
    packages = config.required_packages
    if not packages:
        print("[INFO] No required packages specified in configuration.")
        return
    missing = []
    for pkg in packages:
        status, _ = run_command(f"dpkg -s {pkg}")
        if status != 0:
            missing.append(pkg)
    if missing:
        print(f"[INFO] Installing missing packages: {', '.join(missing)}")
        status, output = run_command(f"sudo apt-get update && sudo apt-get install -y {' '.join(missing)}")
        if status != 0:
            raise RuntimeError(f"[ERROR] Package install failed: {output}")
    else:
        print("[INFO] All required packages are already installed.")

# === Step 1: Detect or Build Toolchain ===
# Uses shared toolchain detection utility from utils.toolchain module.

# === Step 1.5: Ensure Kernel Source Repository ===
# Clone kernel repository if missing or not a valid git directory.

def ensure_kernel_source_repository():
    print("[INFO] Ensuring kernel source repository exists...")
    if not config.kernel_src_dir:
        raise RuntimeError("[ERROR] No kernel_src_dir configured in kernel_build section")
    if not config.repo_url:
        raise RuntimeError("[ERROR] No repo_url configured for kernel repository")
    # Convert to absolute path to prevent issues after directory changes
    config.kernel_src_dir = os.path.abspath(config.kernel_src_dir)
    kernel_src_dir = config.kernel_src_dir
    parent_dir = os.path.dirname(kernel_src_dir)
    if not os.path.exists(parent_dir):
        print(f"[INFO] Creating parent directory: {parent_dir}")
        os.makedirs(parent_dir, exist_ok=True)
    if os.path.exists(kernel_src_dir):
        if os.path.isdir(os.path.join(kernel_src_dir, '.git')):
            print(f"[INFO] Kernel source repository present: {kernel_src_dir}")
            return
        print(f"[WARNING] {kernel_src_dir} exists but is not a git repository; replacing...")
        shutil.rmtree(kernel_src_dir)
    status, output = run_command(f"git clone {config.repo_url} {kernel_src_dir}")
    if status != 0:
        raise RuntimeError(f"[ERROR] Kernel repo clone failed: {output}")
    print(f"[INFO] Cloned kernel repository to: {kernel_src_dir}")

# === Step 2: Robust Upstream Merge with Conflict Handling ===
def run_upstream_merge_script():
    print("[INFO] Running upstream merge script...")
    ensure_kernel_source_repository()
    if not os.path.exists(config.kernel_src_dir):
        raise RuntimeError(f"[ERROR] Kernel source directory {config.kernel_src_dir} missing after clone")
    original_cwd = os.getcwd()
    kernel_parent_dir = os.path.dirname(config.kernel_src_dir)
    os.chdir(kernel_parent_dir)
    try:
        kernel_version = config.target_branch.split('/')[-1] if config.target_branch else "6.12"
        git_obj = GitRepo(
            local_repo=os.path.basename(config.kernel_src_dir),
            upstream_repo_url=config.stable_rt_remote,
            upstream_branch=f"linux-{kernel_version}.y-rt",
            local_base_branch=config.target_branch,
            upstream_repo_name="stable-rt",
            fork_name="origin",
            fork_url=config.repo_url
        )
        os.chdir(config.kernel_src_dir)
        try:
            git_merge_abort()
        except:
            pass
        git_reset(hard=True)
        git_clean(force=True, directories=True, ignored_files=True)
        status, _ = git_fetch()
        if status != 0:
            raise RuntimeError("Failed to fetch remotes")
        status, _ = run_command(f"git checkout -B {config.target_branch} origin/{config.target_branch}")
        if status != 0:
            raise RuntimeError("Failed to checkout target branch")
        status, remotes = git_remote()
        if status == 0 and "stable-rt" not in remotes:
            git_obj.add_remote("stable-rt", config.stable_rt_remote)
        git_fetch("stable-rt", "--tags")
        status, tags = git_tag(list_pattern=f"v{kernel_version}.*-rt*")
        if status != 0 or not tags:
            print(f"[WARNING] No v{kernel_version}-rt tags; skipping merge")
            return
        clean_tags = [t for t in tags.splitlines() if re.match(rf'^v{re.escape(kernel_version)}\.\d+(?:\.\d+)?-rt\d+$', t)]
        if not clean_tags:
            print(f"[WARNING] No clean v{kernel_version}-rt release tags; skipping merge")
            return
        latest_tag = sorted(clean_tags, key=lambda t: list(map(int, re.findall(r'\d+', t))))[-1]
        print(f"[INFO] Latest RT tag: {latest_tag}")
        merge_result = git_obj.merge_branch(latest_tag, f"Merge latest upstream {latest_tag}")
        if merge_result[0] != 0:
            status, conflicts = git_diff(name_only=True, diff_filter="U")
            if status == 0 and conflicts:
                status, git_status_output = git_status()
                concise_body = _format_conflict_email(latest_tag, conflicts, git_status_output, config.target_branch)
                send_email_report(
                    f"Merge conflict report: {config.target_branch}",
                    concise_body
                )
                raise RuntimeError("[ERROR] Merge conflicts detected; email sent")
        else:
            print("[INFO] Merge successful")
    finally:
        os.chdir(original_cwd)

# === Step 3: Build and Deploy Kernel ===
def build_and_deploy_kernel(args):
    try:
        if not args.skip_packages:
            check_required_packages()
        CROSS_COMPILE = detect_or_build_cross_compile(config, script_dir)
        env = os.environ.copy()
        if config.arch:
            env["ARCH"] = config.arch
        env["CROSS_COMPILE"] = CROSS_COMPILE
        if not args.skip_merge:
            run_upstream_merge_script()
        else:
            ensure_kernel_source_repository()
        kernel_src_dir = config.kernel_src_dir
        print("[INFO] Cleaning previous builds...")
        if not args.dry_run:
            status, output = run_command("make mrproper", cwd=kernel_src_dir, env=env)
            if status != 0:
                raise RuntimeError(output)
        kernel_config_target = config.kernel_config or "defconfig"
        print(f"[INFO] Creating kernel configuration: {kernel_config_target}...")
        if not args.dry_run:
            status, output = run_command(f"make {kernel_config_target}", cwd=kernel_src_dir, env=env)
            if status != 0:
                raise RuntimeError(output)
        make_jobs = config.make_jobs or "$(nproc)"
        if make_jobs == "$(nproc)":
            make_jobs = str(os.cpu_count())
        print(f"[INFO] Building kernel and modules with {make_jobs} jobs...")
        if not args.dry_run:
            status, output = run_command(f"make -j{make_jobs} bzImage modules", cwd=kernel_src_dir, env=env)
            if status != 0:
                raise RuntimeError(output)
        temp_modules_dir = config.temp_modules_dir or os.path.join(kernel_src_dir, "tmp-modules")
        print(f"[INFO] Staging modules in: {temp_modules_dir}...")
        if not args.dry_run:
            if os.path.exists(temp_modules_dir):
                shutil.rmtree(temp_modules_dir)
            os.makedirs(temp_modules_dir, exist_ok=True)
            status, output = run_command(f"make modules_install INSTALL_MOD_PATH={temp_modules_dir}", cwd=kernel_src_dir, env=env)
            if status != 0:
                raise RuntimeError(output)
        kernel_version = run_command("make -s kernelrelease", cwd=kernel_src_dir, env=env)[1] if not args.dry_run else "DRY-RUN-VERSION"
        target_host = config.kernel_target_host or config.rt_target_IP
        target_user = config.kernel_target_user or "admin"
        if not target_host:
            raise RuntimeError("[ERROR] No target host configured")
        print(f"[INFO] Copying kernel to target {target_host}...")
        if not args.dry_run:
            status, output = run_command(f"scp {kernel_src_dir}/arch/x86/boot/bzImage {target_user}@{target_host}:/boot/bzImage-{kernel_version}")
            if status != 0:
                raise RuntimeError(output)
        print("[INFO] Backing up existing kernel on target (if needed)...")
        if not args.dry_run:
            status, output = run_command(f"ssh {target_user}@{target_host} 'if [ -f /boot/runmode/bzImage ] && [ ! -h /boot/runmode/bzImage ]; then mv /boot/runmode/bzImage /boot/runmode/bzImage-$(uname -r); else echo Skipping backup; fi'")
            if status != 0:
                print(f"[WARNING] Backup step reported: {output}")
        print("[INFO] Updating bootloader symlink...")
        if not args.dry_run:
            status, output = run_command(f"ssh {target_user}@{target_host} 'ln -sf bzImage-{kernel_version} /boot/runmode/bzImage'")
            if status != 0:
                raise RuntimeError(output)
        print("[INFO] Copying modules to target...")
        if not args.dry_run:
            status, output = execute_and_stream_cmd_output(f"tar cz -C {temp_modules_dir} lib | ssh {target_user}@{target_host} tar xz -C /")
            if status != 0:
                raise RuntimeError(f"[ERROR] Module transfer failed: {output}")
        print("[INFO] Rebooting target...")
        if not args.dry_run:
            status, output = execute_and_stream_cmd_output(f"ssh {target_user}@{target_host} 'reboot' || true")
            if status != 0:
                print(f"[WARNING] Reboot command returned non-zero: {output}")
        if not args.dry_run:
            send_email_report("[SUCCESS] Kernel Build+Install", f"Kernel build and deploy succeeded on {target_host}, running version {kernel_version}")
        else:
            print("[INFO] Dry run completed successfully")
    except Exception as e:
        print(f"[ERROR] {e}")
        if not args.dry_run:
            send_email_report("[FAILURE] Kernel Build+Install", f"Kernel build/deploy failed: {e}")
        sys.exit(1)

# === Main ===
def main():
    global config
    args = parse_args()
    try:
        config = JsonConfig(config_path=args.config, work_item_id=None)
        print(f"[INFO] Loaded configuration from: {args.config}")
        if args.work_dir:
            work_dir = os.path.expandvars(os.path.expanduser(args.work_dir))
            config.kernel_src_dir = os.path.join(work_dir, "linux")
            print(f"[INFO] Using work directory override: {args.work_dir}")
            print(f"[INFO] Kernel source path: {config.kernel_src_dir}")
        if getattr(config, 'kernel_src_dir', None):
            # Convert to absolute path to prevent issues after directory changes
            config.kernel_src_dir = os.path.abspath(config.kernel_src_dir)
            target_host = config.kernel_target_host or config.rt_target_IP or "not configured"
            arch = config.arch or "not configured"
            branch = config.target_branch or "not configured"
            print(f"[INFO] Target: {target_host}, Arch: {arch}, Branch: {branch}")
            print(f"[INFO] Absolute kernel source path: {config.kernel_src_dir}")
        else:
            print("[WARNING] kernel_build section missing or incomplete")
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        sys.exit(1)
    build_and_deploy_kernel(args)

if __name__ == "__main__":
    main()
