from Shell_commands import *

class GitRepo:
    def __init__(self, local_repo, upstream_repo_url, upstream_branch, local_base_branch,remote_repo_name):
        self.local_repo = local_repo
        self.local_base_branch = local_base_branch
        self.upstream_branch = upstream_branch
        self.upstream_repo_url = upstream_repo_url
        self.remote_repo_name = remote_repo_name

    def checkout_branch(self,branch_name):
        """Switch to the given branch."""
        return run_command(f"git checkout {branch_name}")

    def create_branch(self,branch_name):
        """Create a new branch from base_branch."""
        return run_command(f"git checkout -b {branch_name} {self.local_base_branch}")

    def delete_branch(self,branch_name):
        """Delete a local branch."""
        return run_command(f"git branch -D {branch_name}")

    def fetch_branch(self, branch_name):
        """Fetch a remote branch."""
        return run_command(f"git fetch {self.remote_repo_name} {branch_name}")

    def merge_branch(self, branch_name, message = "Merge latest upstream"):
        """Merge a remote branch into the current branch."""
        return run_command(f"git merge {branch_name} --signoff -m {message}", capture_output=True)

    def add_remote(self):
        """Add a new remote."""
        run_command(f"git remote remove {self.remote_repo_name}")
        return run_command(f"git remote add {self.remote_repo_name} {self.upstream_repo_url}")

    def get_current_commit(self):
        """Get the current HEAD commit hash."""
        return run_command("git rev-parse HEAD", capture_output=True)[1]

    def branch_exists(self,branch_name):
        """Check if a branch exists locally."""
        return run_command(f"git rev-parse --verify {branch_name}")[0] == 0

    def diff(self):
        """Check if there are differences in the last merge."""
        return run_command("git diff HEAD~1 HEAD", capture_output=True)

    def pull_latest(self):
        """Pull latest changes from the current branch's remote tracking branch."""
        return run_command("git pull")
    
