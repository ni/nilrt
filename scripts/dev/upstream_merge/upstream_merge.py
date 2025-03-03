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

    checkout_branch(local_base_branch)
    pull_latest()
    add_remote(REMOTE_REPO_NAME, upstream_repo)
    fetch_branch(REMOTE_REPO_NAME, upstream_branch)

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

    create_branch(LOCAL_BRANCH_NAME, local_base_branch)

    commit_before_merge = get_current_commit()
    merge_result = merge_branch(REMOTE_REPO_NAME, upstream_branch)

    if merge_result == 0:
        if get_current_commit() == commit_before_merge:
            print(" ... OK (no changes)")
        elif check_diff():
            print(" ... OK")
        else:
            print(" ... ERRORS")
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
