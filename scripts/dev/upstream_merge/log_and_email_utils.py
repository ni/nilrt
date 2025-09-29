"""
Utilities for logging, formatting merge reports, and sending email
notifications.
"""

import os
import datetime
import logging
from utils.git_commands import send_email


def setup_logging(log_level=10):
    """
    Set up logging configuration.
    :param log_level: Logging level (default: 10).
    """
    global LOG_DIR
    LOG_DIR = f"temp/{datetime.datetime.now().strftime('%d-%m-%Y')}"
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = (
        f"{LOG_DIR}/upstream_merge_"
        f"{datetime.datetime.now().strftime('%H-%M-%S')}.log"
    )
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, mode="a")],
    )


def write_email_headers(email_file_name, email_from,  email_to):
    """
    Write email header information to a log file.

    :param email_file_name: The name of the log file to write to.
    :param email_from: The sender's email address.
    :param email_to: The recipient's email address.
    """
    with open(email_file_name, "w", encoding="utf-8") as log:
        log.write(f"From: {email_from}\n")
        log.write(f"To: {email_to}\n")
        log.write("Subject: Merge Details\n\n")


def format_status(status, message):
    """
    Format the status and message for display/logging.

    :param status: Status code (0 for success, non-zero for errors).
    :param message: Associated message or details.
    :return: Tuple of formatted status strings for summary and detailed logs.
    """
    error_msg = f" ... ERRORS\n    {message or ''}\n\n\n"
    ok_no_changes = " ... OK (no changes)"
    ok_msg = f" ... OK\n    {message}\n\n\n"

    if status != 0:
        return (" ... ERRORS", error_msg)

    if message is None:
        return (ok_no_changes, f"{ok_no_changes}\n\n\n")

    return (" ... OK", ok_msg)


def format_merge_report(merge_report, email_log_level, skip_push_and_pr=False):
    """
    Format the merge report for email or logging.

    The formatted report string is structured as follows:
    - The first line contains the repository name.
    - The second line contains the status of the merge (OK, ERRORS, or no
      changes).
    - The diff is added if there are any changes and if email_log_level is set
      to 1.

    Merge completed successfully:
    sources/bitbake
     ... OK
         Push and PR ... OK

    No changes were detected during the merge:
    sources/bitbake
     ... OK (no changes)

    Errors occurred during the merge:
    sources/bitbake
     ... ERRORS
    """
    min_detail = ""
    error_detail = ""
    diff_detail = ""

    build_and_test_detail = merge_report.pop("Build and Test")
    if build_and_test_detail[0] == 0 and not skip_push_and_pr:
        push_and_pr_details = merge_report.pop("Push and PR")
    # Remove the build/test and PR results from the merge report so that
    # the subsequent loop can focus solely on per-repository merge outcomes.
    # This streamlines the logic and ensures only relevant entries are
    # processed.

    for git_obj, (status, message) in merge_report.items():
        min_line, additional_line = format_status(status, message)

        layer_name = git_obj.local_repo.split("/")[-1]
        min_detail += f"{layer_name}\n{min_line}\n"

        if status != 0:
            error_detail += f"{layer_name}\n{message}\n"

        diff_detail += f"{layer_name}\n{additional_line}"

        if (
            build_and_test_detail[0] == 0
            and not skip_push_and_pr
            and status == 0
            and message is not None
        ):
            git_obj_push_details = push_and_pr_details[git_obj]
            if git_obj_push_details[0] == 0:
                min_detail += "     Push and PR ... OK\n"
                diff_detail += "     Push and PR ... OK\n"
            else:
                min_detail += "     Push and PR ... ERRORS\n"
                error_detail += (
                    f"{git_obj.local_repo}\n{min_line}\n"
                    f"     Push and PR ... ERRORS\n"
                    f"    {git_obj_push_details[1]}\n"
                )
                diff_detail += (
                    "     Push and PR ... ERRORS\n"
                    f"    {git_obj_push_details[1]}\n"
                )

    min_detail += "Build and Test\n"
    if build_and_test_detail[0] == 0:
        min_detail += (
            f"\nBuild and Test\n ... OK\n    {build_and_test_detail[1]}\n"
        )
        diff_detail += (
            f"\nBuild and Test\n ... OK\n    {build_and_test_detail[1]}\n"
        )
    else:
        min_detail += " ... ERRORS\n"
        error_detail += (
            f"\nBuild and Test\n ... ERRORS\n    {build_and_test_detail[1]}\n"
        )
        diff_detail += (
            f"\nBuild and Test\n ... ERRORS\n    {build_and_test_detail[1]}\n"
        )

    if email_log_level == 0:
        return min_detail + "\n\n" + error_detail
    return min_detail + "\n\n" + error_detail + "\n\n" + diff_detail


def write_log(email_file_name, contents):
    """
    Append the given contents to the specified log file.

    :param email_file_name: The name of the log file to write to.
    :param contents: The string content to append to the log file.
    """
    with open(email_file_name, "a", encoding="utf-8") as log:
        log.write(contents)


def write_log_and_send_email(
    email_from, email_to, merge_report, email_log_level, skip_push_and_pr=False
):
    """
    Write the merge report to a log file, then send it as an email.

    :param email_from: The sender's email address.
    :param email_to: The recipient's email address.
    :param merge_report: The merge report data structure.
    :param email_log_level: The log verbosity level for the email.
    :param skip_push_and_pr: Flag to handle the merge report for skipping push
        and PR creation.
    """
    email_file_name = (
        LOG_DIR + "/"
        f"upstream_merge_{datetime.datetime.now().strftime('%H-%M-%S')}.txt"
    )
    formatted_report_string = format_merge_report(
        merge_report, email_log_level, skip_push_and_pr
    )
    write_email_headers(email_file_name, email_from, email_to)
    write_log(email_file_name, formatted_report_string)
    send_email(
        to_address=email_to,
        subject="Merge Details",
        file=email_file_name
    )
