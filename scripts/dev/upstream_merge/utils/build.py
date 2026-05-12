"""
Utility functions for building core feeds and images in the nilrt
project.
"""

import argparse
import os

from .shell_commands import execute_and_stream_cmd_output

config = None
KERNEL_DEFCONFIG = "nati_x86_64_defconfig"


def setup_env_and_build_packages(args="", clean_build=False):
    """
    Build the images for the project.
    This function orchestrates the steps required to build the images,
    including setting up the Docker environment, cleaning build feeds and
    images, and building the core feeds and images.

    :param args: This can be used to select organization-specific build
        configurations.
    :param clean_build: A boolean indicating whether to clean the build feeds
        and images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    # Step 1: Set up the Docker environment
    docker = start_docker_setup()
    if docker[0] != 0:
        return docker
    print("\nDocker setup completed.")

    if clean_build:
        # Step 2: Clean the build feeds and images
        clean = clean_feeds_and_images(args)
        if clean[0] != 0:
            return clean
        print("\nClean feeds and images completed.")

    # Step 2: Build the core feeds
    core_feeds = build_core_feeds(args)
    if core_feeds[0] != 0:
        return core_feeds
    print("\nCore feeds build completed.")

    # Step 3: Build the desirable packages
    desirable_packages = build_desirable_packages(args)
    if desirable_packages[0] != 0:
        return desirable_packages
    print("\nDesirable packages build completed.")

    # Step 4: Build the core images
    core_images = build_core_images(args)
    if core_images[0] != 0:
        return core_images
    print("\nCore images build completed.")

    # Return success if all steps are completed
    return (0, "Building core feeds, safemode and runmode succeeded")


def build_desirable_packages(args=""):
    """
    Build the desirable packages.
    This step involves running the script to build the extra package feed.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nBuilding extra package feed...\n")
    return execute_and_stream_cmd_output(
        f"bash scripts/pipelines/build.desirable.sh {args}"
    )


def clean_feeds_and_images(args=""):
    """
    Clean the build feeds and images.
    This step involves running the script to clean the build feeds and images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nCleaning build feeds and images...\n")
    return execute_and_stream_cmd_output(
        "bash scripts/pipelines/clean.core-feeds_and_core-images.sh "
        f"{args}"
    )


def start_docker_setup():
    """
    Start the Docker setup process.
    This script initializes the Docker environment required for building
    images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nStarting Docker setup...\n")
    return execute_and_stream_cmd_output(
        "bash ./docker/create-build-nilrt.sh"
    )


def build_core_feeds(args=""):
    """
    Build the core feeds.
    This step involves running the script to build the core feeds required
    for the images.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nBuilding core feeds...\n")
    return execute_and_stream_cmd_output(
        "bash scripts/pipelines/build.core-feeds.sh "
        f"{args}"
    )


def build_core_images(args=""):
    """
    Build the core images.
    This step involves running the script to build the core images for the
    project.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    print("\nBuilding core images...\n")
    return execute_and_stream_cmd_output(
        "bash scripts/pipelines/build.core-images.sh "
        f"{args}"
    )


def build_kernel_x86_64(kernel_src_dir):
    print("[INFO] Starting x86_64 kernel build")

    if not os.path.isdir(kernel_src_dir):
        return 1, f"Kernel source directory not found: {kernel_src_dir}"

    # kernel_src_dir = <work-dir>/nilrt-kernel-build/linux
    build_root = os.path.dirname(kernel_src_dir)

    # Read from config
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
    jobs = getattr(config, "kernel_build_jobs", None)

    if jobs is None:
        jobs = "$(nproc)"  # fallback to all available cores

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
        f"make {KERNEL_DEFCONFIG}",
        "make savedefconfig",
        f"mv defconfig arch/x86/configs/{KERNEL_DEFCONFIG}",
    ]

    for cmd in cmds:
        rc = os.system(cmd)
        if rc != 0:
            os.chdir(original_cwd)
            raise RuntimeError(f"[US4][ERROR] Command failed: {cmd}")

    # Check for diff
    diff_rc = os.system(
        f"git diff --quiet arch/x86/configs/{KERNEL_DEFCONFIG}"
    )

    if diff_rc == 0:
        print("[US4] Defconfig unchanged")
        os.chdir(original_cwd)
        return False

    print("[US4] Defconfig changed, creating commit")

    rc = os.system(f"git add arch/x86/configs/{KERNEL_DEFCONFIG}")
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


def parse_args():
    """
    Parse command-line arguments for building the core feeds and images,
    allowing passthrough of extra arguments.
    :return: Tuple of (known_args, unknown_args) as returned by
    argparse.ArgumentParser.parse_known_args().
    """
    parser = argparse.ArgumentParser(
        description="Building core feeds and images", add_help=True
    )
    parser.add_argument(
        "--org",
        dest="org",
        action="store_true",
        help="Pass --org flag to select organization-specific build configs",
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main_args = parse_args()
    ARGS_STR = "--org" if main_args.org else ""
    status_code, message = setup_env_and_build_packages(
        ARGS_STR, clean_build=False
    )
    if status_code == 0:
        print("\nBuild completed successfully.")
    else:
        print(
            f"\nBuild failed with status code {status_code}. Error: {message}"
        )
