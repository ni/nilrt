"""Main script for automating the upstream merge, build, test, and
notification workflow."""

import os
import argparse

from utils.test import install_and_test_image
from json_config import JsonConfig
from utils.git_repo import GitRepo
from upstream_merge import merge_upstream
from utils.push_branch_and_create_pr import push_branch_and_create_pr
from utils.build import setup_env_and_build_packages
from log_and_email_utils import setup_logging, write_log_and_send_email

NILRT_URL = (
    "https://github.com/ni/nilrt.git"
)
META_NILRT_URL = (
    "https://github.com/ni/meta-nilrt.git"
)


def parse_args():
    """
    Parse command-line arguments for the automated repository merging script.

    :return: Parsed arguments as returned by
            argparse.ArgumentParser.parse_args().
    """
    parser = argparse.ArgumentParser(
        description="Automated repository merging script"
    )
    parser.add_argument(
        "-c",
        type=str,
        help="Path to configuration file",
        default="scripts/dev/upstream_merge/automation_conf.json",
    )
    parser.add_argument(
        "-w",
        type=str,
        help="Work item ID",
        default=None,
    )
    parser.add_argument(
        "-s",
        action="store_true",
        help="Skip merging with upstream"
    )
    parser.add_argument(
        "-skip_push_and_pr",
        action="store_true",
        help="Skip pushing and creating PRs"
    )
    args = parser.parse_args()
    return args


def merge_submodules_with_upstream(
    conf_file_path,
    force_checkout,
    username,
    upstream_repo_name,
    merge_branch_name,
    fork_name,
    skip_merge,
):
    """
    Merge submodules with their respective upstream repositories
    as defined in the repos.conf file.

    :param conf_file_path: Path to the configuration file (repos.conf).
    :param force_checkout: Boolean indicating whether to force checkout
        to the base branch.
    :param username: GitHub username owning the downstream fork.
    :param upstream_repo_name: Name of the upstream remote repository.
    :param merge_branch_name: The name of the merge branch to use.
    :param fork_name: The name of the downstream fork repository.
    :param skip_merge: If "True", skip the merge step.
    :return: A dictionary mapping GitRepo objects to (status_code, message).
    """
    merge_report = {}

    with open(os.path.abspath(conf_file_path), "r", encoding="utf-8") as file:
        # Read the configuration file - `repos.conf`
        for line in file:
            if line.startswith("#"):
                continue
            parts = line.split()
            local_repo = parts[0]
            layer_name = local_repo.split("/")[-1]
            token = os.environ.get("GH_PAT")
            if token is None:
                fork_url = f"https://github.com/{username}/{layer_name}.git"
            else:
                fork_url = (
                    f"https://x-access-token:{token}@github.com/"
                    f"{username}/{layer_name}.git"
                )
            git_obj = GitRepo(
                local_repo=local_repo,
                upstream_repo_url=parts[1],
                upstream_branch=parts[2],
                local_base_branch=parts[3],
                upstream_repo_name=upstream_repo_name,
                fork_name=fork_name,
                fork_url=fork_url,
            )
            print(f"\n{layer_name}\n")
            if skip_merge:
                print("\tUpstream Merge has Been Skipped")
                merge_report[git_obj] = (0, "Upstream Merge has Been Skipped")
            else:
                os.chdir(git_obj.local_repo)
                merge_report[git_obj] = merge_upstream(
                    git_obj, force_checkout, merge_branch_name
                )
                os.chdir("../..")

    return merge_report


def build_and_test(clean_build, rt_target_IP, build_args):
    """
    Build images and run tests on a VM if there are no merge errors.

    :param clean_build: Boolean indicating whether to perform a clean build.
    :param rt_target_IP: The target IP address of the RT system.
    :param build_args: To build with NI specific arguments.
    :return: A tuple (status_code, message).
            Returns (0, None) on success, or error details on failure.
    """
    success = setup_env_and_build_packages(build_args, clean_build)
    if success[0] != 0:
        return success
    success = install_and_test_image(rt_target_IP)
    return success


def push_submodules_and_create_PRs(
    merge_report,
    merge_branch_name,
    pr_title,
    pr_description,
    username
):
    """
    For each sub-module that was successfully merged and built, push the merge
    branch to the user's fork and create a pull request targeting the base
    branch. Updates the push_and_pr_results dictionary with the results of
    the push and PR steps.

    :param merge_report: Dictionary mapping GitRepo objects to
                        (status, message).
    :param merge_branch_name: Name of the branch to push and create PRs from.
    :param pr_title: Title for the pull request.
    :param pr_description: Description for the pull request.
    :param username: GitHub username owning the downstream fork.
    :return: Dictionary with push and PR results for each sub-module.
    """
    push_and_pr_results = {}
    for git_obj, (status, message) in list(merge_report.items()):
        if status == 0 and message is not None:
            os.chdir(git_obj.local_repo)
            push_and_pr_results[git_obj] = push_branch_and_create_pr(
                git_obj,
                merge_branch_name,
                username,
                pr_title,
                pr_description
            )

    return push_and_pr_results


def get_pr_description(work_item_id):
    """
    Generate and return the pull request description text.

    :param work_item_id: The work item ID to reference in the PR description.
    :return: A formatted string containing the PR checklist and work item.
    """
    checklist = (
        "- [x] bitbake packagefeed-ni-core\n"
        "- [x] bitbake packagegroup-ni-desirable\n"
        "- [x] bitbake package-index && bitbake nilrt-base-system-image\n"
        "- [x] Installed BSI on a VM and verified it boots successfully"
    )
    work_item_line = (
        f"\n\nAB#{work_item_id}\n"
        if work_item_id is not None else ""
    )
    return (
        f"Merge latest from upstream. No conflicts."
        f"{work_item_line}\n\n{checklist}"
    )


def pull_from_base_branch(branch, upstream_url):
    """
    Pull the latest changes from the NILRT repository.

    :param branch: The branch name to pull.
    :param upstream_url: The URL of the upstream repository.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    git_obj = GitRepo(
        local_base_branch=branch,
        upstream_repo_name="upstream",
        upstream_repo_url=upstream_url,
    )

    add_remote_details = git_obj.add_remote()
    if add_remote_details[0] != 0:
        print(add_remote_details[1])
        return add_remote_details

    pull_details = git_obj.pull()
    if pull_details[0] != 0:
        print(pull_details[1])
        return pull_details

    return (0, None)


def update_meta_nilrt_branch(meta_nilrt_branch):
    """
    Pull the latest changes from the meta-nilrt repository.

    :param meta_nilrt_branch: The branch name to pull from the meta-nilrt repo.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    os.chdir("sources/meta-nilrt")
    # Ensure that the meta-nilrt branch is up to date
    pull_from_meta_nilrt_details = pull_from_base_branch(
        meta_nilrt_branch, META_NILRT_URL
    )
    os.chdir("../..")
    if pull_from_meta_nilrt_details[0] != 0:
        print(pull_from_meta_nilrt_details[1])
        return pull_from_meta_nilrt_details

    return (0, None)


def main():
    """
    Main entry point for the upstream merge automation script.
    Parses arguments, updates repositories, performs merges, builds, tests,
    pushes, creates PRs, and sends a summary email.
    """
    args = parse_args()
    skip_merge = args.s

    json_config_obj = JsonConfig(
        automation_conf_path=args.c,
        work_item_id=args.w
    )

    setup_logging(json_config_obj.log_level)

    # Ensure that the NILRT branch is up to date (important if repos.conf is
    # modified)
    pull_from_nilrt_details = pull_from_base_branch(
        json_config_obj.nilrt_branch,
        NILRT_URL
    )
    if pull_from_nilrt_details[0] != 0:
        print(pull_from_nilrt_details[1])
        return

    merge_report = merge_submodules_with_upstream(
        json_config_obj.conf_file_path,
        json_config_obj.force_checkout,
        json_config_obj.username,
        json_config_obj.upstream_repo_name,
        json_config_obj.merge_branch_name,
        json_config_obj.fork_name,
        skip_merge,
    )

    merge_has_errors = any(
        status != 0 for status, _ in merge_report.values()
    )

    update_meta_nilrt_branch(json_config_obj.meta_nilrt_branch)

    if merge_has_errors:
        print(
            "Merge has errors, skipping build and test."
        )
        build_and_test_details = (1, "Merge has Errors")
    else:
        build_and_test_details = build_and_test(
            clean_build=skip_merge,
            rt_target_IP=json_config_obj.rt_target_IP,
            build_args=json_config_obj.build_args,
        )

        if build_and_test_details[0] == 0 and not args.skip_push_and_pr:
            push_and_pr_results = push_submodules_and_create_PRs(
                merge_report,
                json_config_obj.merge_branch_name,
                "Automated Merge PR",
                get_pr_description(json_config_obj.work_item_id),
                json_config_obj.username,
            )
            merge_report["Push and pr"] = push_and_pr_results

    merge_report["Build and Test"] = build_and_test_details

    write_log_and_send_email(
        json_config_obj.email_from,
        json_config_obj.email_to,
        merge_report,
        json_config_obj.email_log_level,
        args.skip_push_and_pr,
    )


if __name__ == "__main__":
    main()
