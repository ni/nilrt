"""
Utility functions for git operations.
"""

from .shell_commands import run_command


def git_clone(
    repo,
    directory=None,
    depth=None,
    capture_output=True
):
    """
    Clone a Git repository.
    :param repo: URL of the repository to clone.
    :param directory: Directory to clone into (optional).
    :param depth: Depth for shallow cloning (optional).
    :param capture_output: Whether to capture the command output.
    """
    if directory is not None:
        command = f"git clone {repo} {directory}"
    else:
        command = f"git clone {repo}"
    if depth:
        command += f" --depth {depth}"
    return run_command(command, capture_output)


def git_commit(
    message="update",
    amend=False,
    signoff=False,
    capture_output=True
):
    """
    Commit changes to the repository.
    :param message: Commit message.
    :param amend: Whether to amend the previous commit.
    :param signoff: Whether to add a Signed-off-by line.
    :param capture_output: Whether to capture the command output.
    """
    command = "git commit"
    if amend:
        command += " --amend"
    if signoff:
        command += " --signoff"
    command += f' -m "{message}"'
    return run_command(command, capture_output)


def git_push(
    remote_repo_name="origin",
    branch="main",
    force=False,
    delete_existing=False,
    capture_output=True,
):
    """
    Push changes to a remote repository.
    :param remote_repo_name: Name of the remote repository (default: "origin").
    :param branch: Branch to push (default: "main").
    :param force: Whether to force push.
    :param delete_existing: Whether to delete the branch on the remote.
    :param capture_output: Whether to capture the command output.
    """
    if delete_existing:
        command = f"git push {remote_repo_name} --delete {branch}"
    else:
        command = f"git push {remote_repo_name} {branch}"
        if force:
            command += " --force"
    return run_command(command, capture_output)


def git_pull(
    remote=None,
    branch=None,
    rebase=False,
    capture_output=True
):
    """
    Pull the latest changes from a remote repository.
    :param remote: Name of the remote repository (optional).
    :param branch: Branch to pull from (optional).
    :param rebase: Whether to rebase instead of merging.
    :param capture_output: Whether to capture the command output.
    """
    command = "git pull"
    if rebase:
        command += " --rebase"
    if remote is not None and branch is not None:
        command += f" {remote} {branch}"
    return run_command(command, capture_output)


def git_branch(
    branch_name,
    show_current=False,
    create=False,
    delete=False,
    capture_output=True
):
    """
    Handle branch operations: create, delete, or list branches.
    :param branch_name: Name of the branch (required for create or delete).
    :param show_current: Whether to show the current branch.
    :param create: Whether to create a new branch.
    :param delete: Whether to delete the branch.
    :param capture_output: Whether to capture the command output.
    """
    if show_current:
        command = "git branch --show-current"
    elif create:
        command = f"git branch {branch_name}"
    elif delete:
        command = f"git branch -D {branch_name}"
    else:
        command = "git branch"
    return run_command(command, capture_output)


def git_checkout(
    branch_name,
    create=False,
    force_checkout=False,
    capture_output=True
):
    """
    Checkout a branch, creating it if it doesn't exist.
    :param branch_name: Name of the branch to checkout.
    :param force_checkout: Whether to force checkout.
    :param capture_output: Whether to capture the command output.
    """
    if create:
        git_branch(branch_name, create=True)
    if force_checkout:
        command = f"git checkout -f {branch_name}"
    else:
        command = f"git checkout {branch_name}"
    return run_command(command, capture_output)


def git_fetch(
    remote=None,
    branch=None
):
    """
    Fetch the latest changes from a remote repository.
    :param remote: Name of the remote repository (optional).
    :param branch: Branch to fetch (optional).
    """
    command = "git fetch"
    if remote:
        command += f" {remote}"
    if branch:
        command += f" {branch}"
    return run_command(command, capture_output=True)


def git_remote(
    name=None,
    url=None,
    remove=False,
    capture_output=True
):
    """
    Handle listing, adding, and removing remote repositories.
    :param name: Name of the remote repository.
    :param url: URL of the remote repository (required for adding).
    :param remove: Whether to remove the remote repository.
    :param capture_output: Whether to capture the command output.
    """
    if name is not None:
        if url is not None:
            return run_command(f"git remote add {name} {url}", capture_output)
        if remove:
            return run_command(f"git remote remove {name}", capture_output)

    return run_command("git remote", capture_output)


def git_merge(
    branch_name,
    message="Merge Branch",
    no_ff=False,
    signoff=False,
    capture_output=True
):
    """
    Merge a branch into the current branch.
    :param branch_name: Name of the branch to merge.
    :param message: Commit message for the merge.
    :param no_ff: Whether to use a no-fast-forward merge.
    :param signoff: Whether to sign off the merge.
    :param capture_output: Whether to capture the command output.
    """
    if signoff:
        command = (
            f'git merge {branch_name} --signoff -m "{message}"'
        )
    else:
        command = f'git merge {branch_name} -m "{message}"'

    if no_ff:
        command += " --no-ff"
    return run_command(command, capture_output)


def git_diff(
    target="HEAD",
    compare_with=None,
    staged=False,
    name_only=False,
    capture_output=True
):
    """
    Show differences between commits or the working directory.
    :param target: Target commit or branch (default: "HEAD").
    :param compare_with: Commit or branch to compare with (optional).
    :param staged: Whether to show staged changes.
    :param name_only: Show only changed file names.
    :param capture_output: Whether to capture the command output.
    """
    if compare_with:
        command = f"git diff {target} {compare_with}"
    else:
        command = "git diff --staged" if staged else "git diff"
    if name_only:
        command += " --name-only"
    return run_command(command, capture_output)


def git_pull_request(
    title,
    body="",
    repo="",
    base_branch="main",
    head_branch=None,
    capture_output=True
):
    """
    Create a pull request using the GitHub CLI.
    :param title: Title of the pull request.
    :param body: Body/description of the pull request.
    :param base_branch: Base branch for the pull request
                        (default: "main").
    :param head_branch: Head branch for the pull request
                        (default: current branch).
    :param capture_output: Whether to capture the command output.
    """
    if head_branch is None:
        head_branch = run_command(
            "git rev-parse --abbrev-ref HEAD", capture_output=True
        )[1]
    if repo == "":
        command = (
            f'gh pr create --title "{title}" --body "{body}" '
            f'--base {base_branch} --head {head_branch}'
        )
    else:
        command = (
            f'gh pr create --repo {repo} --title "{title}" --body "{body}" '
            f'--base {base_branch} --head {head_branch}'
        )
    return run_command(command, capture_output)


def send_email(
    to_address,
    subject,
    file
):
    """
    Send an email using git send-email.
    :param to_address: Recipient email address.
    :param subject: Subject of the email.
    :param file: File to attach to the email.
    """
    command = (
        f'git send-email --to {to_address} --subject "{subject}" '
        f'--confirm=never --encoding=UTF-8 {file}'
    )
    return run_command(command)
