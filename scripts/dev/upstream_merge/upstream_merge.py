import os
import argparse
from Shell_commands import *
from GitRepo import *

REMOTE_REPO_NAME = "automerge_upstream"
LOCAL_BRANCH_NAME = "dev/automerge/ni"

LOG_FILE = "merge_log.txt"
EMAIL_FROM = "shreejit.c@emerson.com"
EMAIL_TO = "shreejit.c@emerson.com"

def usage():
    print("Usage: script.py [-c <conf file>] [-f] [-h]")

def parse_args():
    parser = argparse.ArgumentParser(description="Automated repository merging script")
    parser.add_argument("-c", type=str, help="Path to configuration file", default="repos.conf")
    parser.add_argument("-f", action="store_true", help="Force checkout, skipping sanity check")
    args = parser.parse_args()

    return (args.c,args.f)

def handle_repo(git_obj,FORCE_CHECKOUT):
    os.chdir(git_obj.local_repo)

    if not FORCE_CHECKOUT and not git_obj.branch_exists(git_obj.local_base_branch):
        return (1,f"\n    Branch {git_obj.local_base_branch} does not exist. Exiting")

    if git_obj.checkout_branch(git_obj.local_base_branch) != (0,None):
        return (1,f"\n    Error switching to branch {git_obj.local_base_branch}. Exiting")

    if git_obj.pull_latest() != (0,None):
        return (1,f"\n    Error pulling latest on {git_obj.local_base_branch}. Exiting")

    git_obj.add_remote()

    if git_obj.fetch_branch(git_obj.upstream_branch) != (0,None):
        return (1,f"\n    Error fetching {git_obj.upstream_branch} from {REMOTE_REPO_NAME}. Exiting")

    if git_obj.branch_exists(LOCAL_BRANCH_NAME):
        git_obj.checkout_branch(git_obj.local_base_branch)
        git_obj.delete_branch(LOCAL_BRANCH_NAME)

    if git_obj.create_branch(LOCAL_BRANCH_NAME) != (0,None):
        return (1,f"\n    Error creating {LOCAL_BRANCH_NAME}. Exiting")

    commit_before_merge = git_obj.get_current_commit()
    
    merge_result = git_obj.merge_branch(f"{REMOTE_REPO_NAME} {git_obj.upstream_branch}")

    if merge_result[0] == 0:
        diff_output=git_obj.diff()
        if (git_obj.get_current_commit() == commit_before_merge) or diff_output == (0,None):
            return (0,None)
        else:
            return (0,diff_output[1])
    else:
        return (1,merge_result[1])
    
def send_email(to, file):
    """ Send Mail """
    return run_command(["git", "send-email", "--to", to, "--subject", "Merge Details", file])

def format_email(output_report):
    with open(LOG_FILE, "w") as log:
        log.write(f"From: {EMAIL_FROM}\n")
        log.write(f"To: {EMAIL_TO}\n")
        log.write("Subject: Merge Details\n\n")

        for local_repo,output in output_report:
            log.write(f"{local_repo}\n")
            if output[0]==1:
                log.write(" ... ERRORS\n")
                log.write(f"{output[1]}\n")
            else:
                if output[1] == None:
                    log.write(" ... OK (no changes)\n")
                else:
                    log.write(" ... OK\n")
                    log.write(f"{output[1]}\n")


def main(CONF_FILE,FORCE_CHECKOUT):
    current_directory = os.getcwd()
    output_report = {}
    with open(CONF_FILE, "r") as file:
        for line in file:
            if line.startswith("#"):
                continue
            parts = line.split()
            git_obj=GitRepo(parts[0],parts[1],parts[2],parts[3],REMOTE_REPO_NAME)
            output_report[parts[0]] = handle_repo(git_obj,FORCE_CHECKOUT)
            os.chdir(current_directory)

    format_email(output_report)
    send_email(EMAIL_TO,LOG_FILE)

if __name__ == "__main__":
    CONF_FILE,FORCE_CHECKOUT = parse_args()
    main(CONF_FILE,FORCE_CHECKOUT)
