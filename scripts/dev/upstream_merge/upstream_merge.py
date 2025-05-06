"""
Workflow for automating the upstream merge process for submodules and
repositories.
"""


def merge_upstream(git_obj, force_checkout, merge_branch_name):
    """
    Merge the latest changes from the upstream branch.

    :param git_obj: The GitRepo object to interact with the repository.
    :param force_checkout: Boolean indicating whether to force checkout to
        the base branch.
    :param merge_branch_name: The name of the merge branch to use.
    :return: A tuple (status_code, message). Returns (0, None) if no changes or
        (0, diff) if merged.
    """
    merge_prepare_details = prepare_for_merge(git_obj, force_checkout)
    if merge_prepare_details[0] != 0:
        return merge_prepare_details

    repo_details = create_merge_branch(git_obj, merge_branch_name)
    if repo_details[0] != 0:
        return repo_details

    commit_before_merge = git_obj.get_current_commit()

    merge_result = git_obj.merge_branch(
        f"{git_obj.upstream_repo_name}/{git_obj.upstream_branch}",
        "Merge latest upstream",
    )

    if merge_result[0] == 0:
        diff_output = git_obj.diff()
        if (git_obj.get_current_commit() == commit_before_merge) or \
                diff_output == (0, "",):
            return (0, None)  # No changes after merge [... OK (no changes)]
        return (0, diff_output[1])  # Changes were merged successfully [... OK]

    return (1, merge_result[1])  # Merge failed [... ERRORS]


def prepare_for_merge(git_obj, force_checkout):
    """
    Prepare the repository for merging by switching to the base branch, pulling
    the latest changes, fetching from upstream, and creating the merge branch.

    :param git_obj: The GitRepo object to interact with the repository.
    :param force_checkout: Boolean indicating whether to force checkout
        the base branch.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """

    base_branch_details = switch_to_base_branch_and_pull(
        git_obj,
        force_checkout
        )
    if base_branch_details[0] != 0:
        return base_branch_details

    fetch_details = fetch_upstream(git_obj)
    if fetch_details[0] != 0:
        return fetch_details

    return (0, None)


def switch_to_base_branch_and_pull(git_obj, force_checkout):
    """
    Switch to the base branch, optionally force checkout,
    set the origin remote, and pull the latest changes.

    :param git_obj: The GitRepo object to interact with the repository.
    :param force_checkout: Boolean indicating whether to force checkout
        the base branch.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    if not force_checkout:
        branch_details = git_obj.branch_exists(git_obj.local_base_branch)
        if not branch_details:
            print(
                f"\n    Branch {git_obj.local_base_branch} does not exist. "
                "Exiting"
            )
            return (
                1,
                f"\n    Branch {git_obj.local_base_branch} does not exist. "
                "Exiting",
            )

    checkout_details = git_obj.checkout_branch(
        git_obj.local_base_branch, force_checkout=force_checkout
    )
    if checkout_details[0] != 0:
        print(checkout_details[1])
        return checkout_details

    set_origin_details = git_obj.add_remote(
        "origin",
        f"https://github.com/ni/{git_obj.local_repo.split('/')[-1]}.git"
    )
    if set_origin_details[0] != 0:
        print(set_origin_details[1])
        return set_origin_details

    pull_details = git_obj.pull(
        branch_name=git_obj.local_base_branch, upstream_repo_name="origin"
    )
    if pull_details[0] != 0:
        print(pull_details[1])
        return pull_details

    return (0, None)


def fetch_upstream(git_obj):
    """
    Add the upstream remote and fetch the latest changes from the upstream
    repository.

    :param git_obj: The GitRepo object to interact with the repository.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    add_remote_details = git_obj.add_remote()
    if add_remote_details[0] != 0:
        print(add_remote_details[1])
        return add_remote_details

    fetch_details = git_obj.fetch_branch()
    if fetch_details[0] != 0:
        print(fetch_details[1])
        return fetch_details

    return (0, None)


def create_merge_branch(git_obj, merge_branch_name):
    """
    Create and check out a new merge branch, deleting it first if it already
    exists.

    :param git_obj: The GitRepo object to interact with the repository.
    :param merge_branch_name: The name of the merge branch to create.
    :return: A tuple (status_code, message). Returns (0, None) on success.
    """
    if git_obj.branch_exists(merge_branch_name):
        git_obj.checkout_branch(git_obj.local_base_branch)
        git_obj.delete_branch(merge_branch_name)

    checkout_details = git_obj.checkout_branch(merge_branch_name, create=True)
    if checkout_details[0] != 0:
        print(checkout_details[1])
        return checkout_details

    return (0, None)
