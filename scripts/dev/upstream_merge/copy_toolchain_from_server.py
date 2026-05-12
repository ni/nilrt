import os

# --------------------
# Nirvana mount base (assumed present)
# --------------------
NIRVANA_SDK_BASE = (
    "/mnt/nirvana/perforceExports/build/exports/"
    "ni/rtos/rtos_toolchain/official/export"
)


def _get_latest_major_version():
    if not os.path.isdir(NIRVANA_SDK_BASE):
        return None

    versions = []
    for d in os.listdir(NIRVANA_SDK_BASE):
        path = os.path.join(NIRVANA_SDK_BASE, d)
        if os.path.isdir(path):
            try:
                versions.append((tuple(map(int, d.split("."))), d))
            except ValueError:
                continue

    return sorted(versions)[-1][1] if versions else None


def _get_latest_build_version(version_path):
    builds = []
    for d in os.listdir(version_path):
        path = os.path.join(version_path, d)
        if os.path.isdir(path):
            try:
                builds.append((
                    list(map(int, d.replace("d", ".").split("."))), d))
            except ValueError:
                continue

    return sorted(builds)[-1][1] if builds else None


def copy_toolchain_from_nirvana(build_root):
    """
    Copy latest x64 NILRT toolchain from mounted Nirvana to:
      <build_root>/toolchain/NILinuxRT-x64
    """

    latest_version = _get_latest_major_version()
    if not latest_version:
        return 1, "No Nirvana toolchain versions found"

    version_path = os.path.join(NIRVANA_SDK_BASE, latest_version)
    latest_build = _get_latest_build_version(version_path)
    if not latest_build:
        return 1, f"No builds found under Nirvana version {latest_version}"

    sdk_src = os.path.join(
        version_path,
        latest_build,
        "toolchain",
        "sdk",
        "NILinuxRT-x64"
    )

    if not os.path.isdir(sdk_src):
        return 1, f"x64 SDK not found at: {sdk_src}"

    toolchain_root = os.path.join(build_root, "toolchain")
    toolchain_dst = os.path.join(toolchain_root, "NILinuxRT-x64")

    # Idempotent: skip if already present
    if os.path.isdir(toolchain_dst):
        return 0, f"Toolchain already present at {toolchain_dst}", toolchain_dst

    os.makedirs(toolchain_root, exist_ok=True)

    ret = os.system(f"cp -r {sdk_src} {toolchain_root}/")
    if ret != 0:
        return 1, "Failed to copy toolchain from Nirvana"

    return 0, (
        f"Toolchain copied from Nirvana\n"
        f"Version: {latest_version}/{latest_build}\n"
        f"Location: {toolchain_dst}"
    ), toolchain_dst


def prepare_toolchain_environment(toolchain_dst):
    """
    Run the NILinuxRT SDK installer (non-interactive) if needed,
    extracting into the local build toolchain directory,
    then source the environment.
    """

    if not os.path.isdir(toolchain_dst):
        return 1, f"Toolchain directory not found: {toolchain_dst}"

    env_script = None
    for root, dirs, files in os.walk(toolchain_dst):
        for f in files:
            if f.startswith("environment-setup"):
                env_script = os.path.join(root, f)
                break
        if env_script:
            break

    # If SDK is not yet extracted, run installer
    if not env_script:
        installer = next(
            (f for f in os.listdir(toolchain_dst) if f.endswith(".sh")),
            None
        )
        if not installer:
            return 1, "No SDK installer (.sh) found in toolchain directory"

        installer = os.path.join(toolchain_dst, installer)

        os.chmod(installer, 0o755)

        # IMPORTANT: force extraction into toolchain_dst
        ret = os.system(
            f'bash "{installer}" -y -d "{toolchain_dst}"'
        )
        if ret != 0:
            return 1, "Failed to run SDK installer"

        # Look again for environment-setup after extraction
        for root, dirs, files in os.walk(toolchain_dst):
            for f in files:
                if f.startswith("environment-setup"):
                    env_script = os.path.join(root, f)
                    break
            if env_script:
                break

        if not env_script:
            return 1, "installer ran , env-setup script not found"

    # Source environment into Python process
    cmd = f'bash -c "source {env_script} >/dev/null && env"'
    with os.popen(cmd) as proc:
        for line in proc:
            key, _, value = line.strip().partition("=")
            os.environ[key] = value

# CROSS_COMPILE is expected to be exported by the SDK environment-setup script

    if "CROSS_COMPILE" not in os.environ:
        return 1, (
            "CROSS_COMPILE not set after sourcing toolchain environment. "
            "Ensure the SDK environment-setup script exports it correctly."
        )

    print(f"[TOOLCHAIN] CROSS_COMPILE set to: {os.environ['CROSS_COMPILE']}")

    return 0, "Toolchain environment ready"
