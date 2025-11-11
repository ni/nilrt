"""Provides utilities for reading and validating the automation_conf.json
    configuration file."""

import json
import os


class JsonConfig:
    """Handles loading and validating the automation_conf.json
        configuration file."""

    def __init__(self, automation_conf_path, work_item_id):
        with open(automation_conf_path, "r", encoding="utf-8") as file:
            config = json.load(file)
        self.work_item_id = work_item_id
        self.nilrt_branch = config.get("nilrt_branch")
        self.meta_nilrt_branch = config.get("meta_nilrt_branch")
        self.conf_file_path = os.getcwd() + f"/{config.get('conf_file_path')}"
        self.force_checkout = config.get("force_checkout")
        self.upstream_repo_name = config.get("upstream_repo_name")
        self.merge_branch_name = config.get("merge_branch_name")
        self.username = config.get("username")
        self.fork_name = config.get("fork_name")
        self.email_from = config.get("email_from")
        self.email_to = config.get("email_to")
        self.email_log_level = config.get("email_log_level")
        self.log_level = config.get("log_level")
        self.build_args = config.get("build_args", "")
        self.rt_target_IP = config.get("rt_target_IP")
        
        # Kernel build configuration (optional section)
        kernel_config = config.get("kernel_build", {})
        # Expand environment variables in paths
        self.kernel_src_dir = self._expand_path(kernel_config.get("kernel_src_dir"))
        self.kernel_target_host = kernel_config.get("target_host")
        self.kernel_target_user = kernel_config.get("target_user")
        self.arch = kernel_config.get("arch")
        self.temp_modules_dir = self._expand_path(kernel_config.get("temp_modules_dir"))
        self.toolchain_prefix = self._expand_path(kernel_config.get("toolchain_prefix"))
        self.merge_workdir = self._expand_path(kernel_config.get("merge_workdir"))
        self.repo_url = kernel_config.get("repo_url")
        self.target_branch = kernel_config.get("target_branch")
        self.stable_rt_remote = kernel_config.get("stable_rt_remote")
        self.nilrt_root = self._expand_path(kernel_config.get("nilrt_root"))
        self.required_packages = kernel_config.get("required_packages", [])
        self.make_jobs = kernel_config.get("make_jobs", "$(nproc)")
        self.kernel_config = kernel_config.get("kernel_config", "defconfig")
    
    def _expand_path(self, path):
        """Expand environment variables and user home directory in paths."""
        if path:
            return os.path.expandvars(os.path.expanduser(path))
        return path
        
    def get_toolchain_gcc_path(self):
        """Get the full path to the toolchain GCC binary."""
        if self.toolchain_prefix:
            return self.toolchain_prefix + "gcc"
        return None
    
    def get_sdk_dir(self):
        """Get the SDK directory path."""
        if self.nilrt_root:
            return os.path.join(self.nilrt_root, "build", "tmp-glibc", "deploy", "sdk")
        return None
    
    def get_toolchain_build_script(self):
        """Get the path to the toolchain build script."""
        if self.nilrt_root:
            return os.path.join(self.nilrt_root, "scripts", "pipelines", "build.toolchain.sh")
        return None
