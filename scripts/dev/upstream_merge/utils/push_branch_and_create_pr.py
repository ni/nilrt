"""
Functions for pushing branches to forks and creating pull requests.
"""

import sys
import argparse

from .git_repo import GitRepo


def push_branch_and_create_pr(
    git_obj,
    branch_name,
    username,
    pr_title,
    pr_description
):
    """
    Push the specified branch to the fork remote and create a pull request.

    :param git_obj: The GitRepo object to interact with the repository.
    :param branch_name: The name of the branch to push and create a PR from.
    :param work_item_id: The work item ID to reference in the PR description.
    :param username: The GitHub username owning the downstream fork.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    push_details = push_branch(git_obj, branch_name)
    if push_details[0] != 0:
        print(push_details[1])
        return push_details

    pr_details = create_pr(
        git_obj,
        branch_name,
        username,
        pr_title,
        pr_description
    )
    if pr_details[0] != 0:
        print(pr_details[1])
        return pr_details

    return (0, None)


def push_branch(
    git_obj,
    branch_name
):
    """
    Push the specified branch to the fork remote,
    deleting it first if it already exists.

    :param git_obj: The GitRepo object to interact with the repository.
    :param branch_name: The name of the branch to push.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    add_remote_details = git_obj.add_remote(
                            git_obj.fork_name,
                            git_obj.fork_url
                        )
    if add_remote_details[0] != 0:
        print(add_remote_details[1])
        return add_remote_details

    if git_obj.branch_exists(
        branch_name,
        git_obj.fork_name,
        check_on_remote=True
    ):
        push_delete_details = git_obj.push(
            branch_name, git_obj.fork_name, delete_existing=True
        )
        if push_delete_details[0] != 0:
            print(push_delete_details[1])
            return push_delete_details

    push_details = git_obj.push(branch_name, git_obj.fork_name)
    if push_details[0] != 0:
        print(push_details[1])
        return push_details

    return (0, None)


def create_pr(
    git_obj,
    branch_name,
    username,
    pr_title,
    pr_description=None
):
    """
    Create a pull request using the provided GitRepo object.

    :param git_obj: The GitRepo object to interact with the repository.
    :param branch_name: The name of the branch where the merge was performed.
    :param username: The GitHub username owning the downstream fork.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    pr_details = git_obj.create_pull_request(
        title=pr_title,
        body=pr_description,
        base_branch=git_obj.local_base_branch,
        head_branch=f"{username}:{branch_name}",
    )
    if pr_details[0] != 0:
        print(pr_details[1])
        return pr_details

    return (0, None)


def parse_args():
    """
    Parse command-line arguments for the Push and PR script.

    :return: Parsed arguments as returned by
            argparse.ArgumentParser.parse_args().
    """
    parser = argparse.ArgumentParser(description="Push and PR script")
    parser.add_argument(
        "-t", type=str, help="Pull request title", default="Automated Merge PR"
    )
    parser.add_argument("-u", type=str, help="Username", default=None)
    parser.add_argument("-br", type=str, help="Branch name", default=None)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    git_obj = GitRepo(local_base_branch=args.br)

    status_code, message = push_branch_and_create_pr(
        git_obj, git_obj.local_base_branch, args.u, args.t, None
    )
    if status_code != 0:
        print(f"Error code: {status_code}, message: {message}")
        sys.exit()

    print("Push and PR created successfully.")
