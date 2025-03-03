import os
import sys
import argparse
from git_commands import *

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
    args = parser.parse_args()

    CONF_FILE = args.c
    FORCE_CHECKOUT = args.f

def handle_repo(local_repo, upstream_repo, upstream_branch, local_base_branch):
    temp = os.getcwd()
    os.chdir(local_repo)
    print(local_repo, end="")

    if not FORCE_CHECKOUT and not branch_exists(local_base_branch):
        print(f"\n    Branch {local_base_branch} does not exist. Exiting")
        sys.exit(1)

    if checkout_branch(local_base_branch) != (0,None):
        print(f"\n    Error switching to branch {local_base_branch}. Exiting")
        sys.exit(1)
    if pull_latest() != (0,None):
        print(f"\n    Error pulling latest on {local_base_branch}. Exiting")
        sys.exit(1)
    add_remote(REMOTE_REPO_NAME, upstream_repo) 
    if fetch_branch(REMOTE_REPO_NAME, upstream_branch) != (0,None):
        print(f"\n    Error fetching {upstream_branch} from {REMOTE_REPO_NAME}. Exiting")
        sys.exit(1)

    if branch_exists(LOCAL_BRANCH_NAME):
        while True:
            response = input(f"\n    Branch {LOCAL_BRANCH_NAME} already exists\n"
                             "    Delete Branch(d)/Skip Repo(s)/Cancel Merge(c)? ").lower()
            if response.startswith("d"):
                checkout_branch(local_base_branch)
                delete_branch(LOCAL_BRANCH_NAME)
                break
            elif response.startswith("s"):
                os.chdir(temp)
                return
            elif response.startswith("c"):
                print("Exiting")
                sys.exit(0)
            else:
                print("    Please answer d/s/c")

    if create_branch(LOCAL_BRANCH_NAME, local_base_branch) != (0,None):
        print(f"\n    Error creating {LOCAL_BRANCH_NAME}. Exiting")
        sys.exit(1)

    commit_before_merge = get_current_commit()
    merge_result = merge_branch(REMOTE_REPO_NAME, upstream_branch)

    if merge_result[0] == 0:
        if (get_current_commit() == commit_before_merge) or check_diff() == 0:
            print(" ... OK (no changes)")
        else:
            print(" ... OK")
            print_diff()
    else:
        print(" ... ERRORS")
        print(merge_result)



    os.chdir(temp)

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
