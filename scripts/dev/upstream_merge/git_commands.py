import subprocess
import sys

def run_git_command(command, capture_output=False):
    """
    Run a git command and handle errors.

    :param command: List of Git command arguments.
    :param capture_output: Whether to capture the output.
    :return: (return_code, output) - return code and output string.
    """
    try:
        if capture_output:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            return result.returncode, result.stdout.strip()
        else:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode, None
    except Exception as e:
        print(f"Error running command: {' '.join(command)}")
        print(e)
        sys.exit(1)

def checkout_branch(branch_name):
    """Switch to the given branch."""
    return run_git_command(["git", "checkout", branch_name])

def create_branch(branch_name, base_branch):
    """Create a new branch from base_branch."""
    return run_git_command(["git", "checkout", "-b", branch_name, base_branch])

def delete_branch(branch_name):
    """Delete a local branch."""
    return run_git_command(["git", "branch", "-D", branch_name])

def fetch_branch(remote_name, branch_name):
    """Fetch a remote branch."""
    return run_git_command(["git", "fetch", remote_name, branch_name])

def merge_branch(remote_name, branch_name, message="Merge latest upstream"):
    """Merge a remote branch into the current branch."""
    return run_git_command(["git", "merge", f"{remote_name}/{branch_name}", "--signoff", "-m", message])

def add_remote(remote_name, remote_url):
    """Add a new remote."""
    run_git_command(["git", "remote", "remove", remote_name])  # Remove if exists
    return run_git_command(["git", "remote", "add", remote_name, remote_url])

def get_current_commit():
    """Get the current HEAD commit hash."""
    return run_git_command(["git", "rev-parse", "HEAD"], capture_output=True)[1]

def branch_exists(branch_name):
    """Check if a branch exists locally."""
    return run_git_command(["git", "rev-parse", "--verify", branch_name])[0] == 0

def check_diff():
    """Check if there are differences in the last merge."""
    return "diff" in run_git_command(["git", "diff", "HEAD~1", "HEAD"], capture_output=True)[1]

def print_diff():
    """Check if there are differences in the last merge."""
    return run_git_command(["git", "diff", "HEAD~1", "HEAD"], capture_output=True)[1]

def pull_latest():
    """Pull latest changes from the current branch's remote tracking branch."""
    return run_git_command(["git", "pull"])
