import os
import sys
import argparse
import subprocess

CONF_FILE = None
REMOTE_REPO_NAME = "automerge_upstream"
LOCAL_BRANCH_NAME = "dev/automerge/ni"
FORCE_CHECKOUT = False

def usage():
    print("Usage: script.py [-c <conf file>] [-f] [-h]")

def parse_args():
    global CONF_FILE, FORCE_CHECKOUT
    parser = argparse.ArgumentParser(description="Automated repository merging script")
    parser.add_argument("-c", type=str, help="Path to configuration file", default="repos.conf")
    parser.add_argument("-f", action="store_true", help="Force checkout, skipping sanity check")
    parser.add_argument("-h", action="help", help="Show this help message and exit")
    args = parser.parse_args()

    CONF_FILE = args.c
    FORCE_CHECKOUT = args.f

def sanity_test_repo(local_base_branch):
    if FORCE_CHECKOUT:
        print("\n    Force checkout enabled. Skipping sanity check.")
    else:
        result = subprocess.run(["git", "rev-parse", "--verify", local_base_branch],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            print(f"\n    Branch {local_base_branch} does not exist. Exiting")
            sys.exit(1)

def update_local_base_branch(local_base_branch):
    result = subprocess.run(["git", "checkout", local_base_branch],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        result = subprocess.run(["git", "pull"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            print(f"\n    Error pulling latest on {local_base_branch}. Exiting")
            sys.exit(1)
    else:
        print(f"\n    Error switching to branch {local_base_branch}. Exiting")
        sys.exit(1)

def add_remote(upstream_repo):
    subprocess.run(["git", "remote", "remove", REMOTE_REPO_NAME],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "remote", "add", REMOTE_REPO_NAME, upstream_repo])

def fetch_remote_branch(upstream_branch):
    result = subprocess.run(["git", "fetch", REMOTE_REPO_NAME, upstream_branch],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        print(f"\n    Error fetching {upstream_branch} from {REMOTE_REPO_NAME}. Exiting")
        sys.exit(1)

def handle_existing_local_branch(local_base_branch):
    while True:
        response = input(f"\n    Branch {LOCAL_BRANCH_NAME} already exists\n"
                         "    Delete Branch(d)/Skip Repo(s)/Cancel Merge(c)? ").lower()
        if response.startswith("d"):
            result = subprocess.run(["git", "checkout", local_base_branch],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode != 0:
                print(f"\n    Error switching to branch {local_base_branch}. Exiting")
                sys.exit(1)
            subprocess.run(["git", "branch", "-D", LOCAL_BRANCH_NAME], stdout=subprocess.DEVNULL)
            return 0
        elif response.startswith("s"):
            return 1
        elif response.startswith("c"):
            print("Exiting")
            sys.exit(0)
        else:
            print("    Please answer d/s/c")

def create_local_branch(local_base_branch):
    result = subprocess.run(["git", "rev-parse", "--verify", LOCAL_BRANCH_NAME],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        if handle_existing_local_branch(local_base_branch):
            return 1

    result = subprocess.run(["git", "checkout", "-b", LOCAL_BRANCH_NAME, local_base_branch],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        print(f"\n    Error creating {LOCAL_BRANCH_NAME}. Exiting")
        sys.exit(1)
    return 0

def is_non_empty_merge(commit_before_merge):
    commit_after_merge = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if commit_before_merge == commit_after_merge:
        return 1

    diff_result = subprocess.run(["git", "diff", "HEAD~1", "HEAD"], capture_output=True, text=True).stdout.strip()
    return 0 if "diff" in diff_result else 1

def merge_upstream_branch(upstream_branch):
    commit_before_merge = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    result = subprocess.run(["git", "merge", f"{REMOTE_REPO_NAME}/{upstream_branch}", "--signoff", "-m", "Merge latest upstream"],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        if is_non_empty_merge(commit_before_merge) == 0:
            print(" ... OK")
        else:
            print(" ... OK (no changes)")
    else:
        print(" ... ERRORS")

def handle_repo(local_repo, upstream_repo, upstream_branch, local_base_branch):
    os.chdir(local_repo)
    print(local_repo, end="")

    sanity_test_repo(local_base_branch)
    update_local_base_branch(local_base_branch)
    add_remote(upstream_repo)
    fetch_remote_branch(upstream_branch)
    if create_local_branch(local_base_branch) != 0:
        print(" ... SKIPPED")
    else:
        merge_upstream_branch(upstream_branch)

def main():
    with open(CONF_FILE, "r") as file:
        for line in file:
            if line.startswith("#"):
                continue
            parts = line.split()
            local_repo, upstream_repo, upstream_branch, local_base_branch = parts
            handle_repo(local_repo, upstream_repo, upstream_branch, local_base_branch)

if __name__ == "__main__":
    parse_args()
    main()
