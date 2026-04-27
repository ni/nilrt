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
        self.ssh_connection = config.get("ssh_connection")
