 """Toolchain detection/build helper: auto-detect existing repo first (ancestor walk),
ignore nilrt_root hint if already inside a clone; only clone when nothing usable exists."""
import os
from .shell_commands import run_command
from .git_commands import git_clone

BUILD_SCRIPT_REL = os.path.join('scripts', 'pipelines', 'build.toolchain.sh')

def _has_build_script(root):
    return root and os.path.isfile(os.path.join(root, BUILD_SCRIPT_REL))

def _walk_up_for_build_script(start_dir):
    cur = os.path.abspath(start_dir)
    while True:
        if _has_build_script(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:  # reached filesystem root
            return None
        cur = parent

def detect_or_build_cross_compile(config, script_dir):
    """Return CROSS_COMPILE prefix, building toolchain/SDK if missing.
    Order:
      1. Ancestor of script_dir containing build.toolchain.sh (preferred)
      2. Provided hint (config.nilrt_root) if ancestor not found
      3. Clone into expanded hint (or ~/nilrt-sdk if empty) if still missing
    """
    gcc_binary = config.get_toolchain_gcc_path()
    if gcc_binary and os.path.isfile(gcc_binary):
        print(f"[INFO] Found CROSS_COMPILE: {config.toolchain_prefix}")
        return config.toolchain_prefix
    if not config.toolchain_prefix:
        raise RuntimeError('[ERROR] No toolchain_prefix configured')

    chosen_root = _walk_up_for_build_script(script_dir)
    if chosen_root:
        print(f"[INFO] Auto-detected existing nilrt root: {chosen_root}")
    else:
        hint = getattr(config, 'nilrt_root', '') or 'nilrt-sdk'
        if not os.path.isabs(hint):
            hint = os.path.join(os.path.expanduser('~'), hint)
        if _has_build_script(hint):
            chosen_root = hint
            print(f"[INFO] Using hinted nilrt_root with build script: {chosen_root}")
        else:
            # Need to clone
            if not os.path.exists(hint):
                os.makedirs(hint, exist_ok=True)
            print(f"[INFO] Cloning nilrt repo into {hint} (no existing build.toolchain.sh found)...")
            status, _ = git_clone('https://github.com/ni/nilrt.git', hint)
            if status != 0:
                raise RuntimeError('[ERROR] Failed to clone nilrt repo for toolchain build')
            chosen_root = hint
    config.nilrt_root = chosen_root
    build_script = os.path.join(chosen_root, BUILD_SCRIPT_REL)
    if not os.path.isfile(build_script):
        raise RuntimeError(f"[ERROR] build.toolchain.sh missing at {build_script}")

    print('[WARNING] CROSS_COMPILE not found, building toolchain...')
    status, _ = run_command(f"bash {build_script}", cwd=chosen_root)
    if status != 0:
        raise RuntimeError('[ERROR] Toolchain build script failed')

    sdk_dir = config.get_sdk_dir()
    if sdk_dir and os.path.exists(sdk_dir):
        installers = [f for f in os.listdir(sdk_dir) if f.endswith('.sh')]
        if installers:
            installer = os.path.join(sdk_dir, installers[0])
            print('[INFO] Installing SDK to /usr/local/oecore-x86_64 ...')
            status, _ = run_command(f"sudo bash {installer} -d /usr/local/oecore-x86_64 -y")
            if status != 0:
                raise RuntimeError('[ERROR] SDK installer failed')
        else:
            print(f'[WARNING] No SDK installer found in {sdk_dir}')
    else:
        print(f'[WARNING] SDK directory {sdk_dir} does not exist')

    gcc_binary = config.get_toolchain_gcc_path()
    if gcc_binary and os.path.isfile(gcc_binary):
        print(f"[INFO] Successfully built CROSS_COMPILE: {config.toolchain_prefix}")
        return config.toolchain_prefix
    raise RuntimeError(f'[ERROR] Toolchain build completed, but compiler still missing at expected path: {gcc_binary}')
