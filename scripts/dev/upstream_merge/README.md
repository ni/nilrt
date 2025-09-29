# MOTIVATION

To ensure the long-term maintainability and efficiency of the ni/nilrt repository, automating the upstream merge process is a crucial step. Manual upstream merges are often tedious, time-consuming, and prone to human error, especially as the size and frequency of upstream changes grow. By automating this process, we can significantly reduce the cost of maintenance by saving several hours of manual effort per release cycle. This allows developers to focus more on value-adding tasks rather than routine integration work. Automation also ensures that our fork stays closely aligned with upstream changes, minimizing future integration conflicts and making it easier to adopt new features, security patches, and bug fixes promptly. Overall, this improves the quality, stability, and security of the codebase while enhancing the team's productivity and responsiveness to upstream evolution.

The script does the following tasks:
- Automatically merges changes from upstream repositories into the local fork, reducing manual effort.
- Builds the safemode and runmode images after a successful merge to ensure the codebase is functional.
- Installs and tests these images on a RT target via SSH to verify that the integration is successful and the target works as expected.
- Commits and pushes the new changes and creates a PR targeting the main branch.
- Sends email reports about the merge and build status.

Overall, it streamlines and safeguards the process of keeping the local fork up-to-date with upstream changes, ensuring quality and reducing maintenance overhead.

---

## **Script Overview**

### **Workflow for Each Submodule in the `nilrt` Repository**

1. **Check Out the Base Branch**:
   - The script checks out the base branch as specified in the [`repos.conf`](./repos.conf) file.

2. **Pull the Upstream Branch**:
   - The upstream branch mentioned in [`repos.conf`](./repos.conf) is pulled to ensure the latest changes are fetched.

3. **Merge the Two Branches**:
   - The base branch and the upstream branch are merged.
   - The script reports whether the merge was successful or if it encountered any conflicts.

4. **Build Images on Successful Merge**:
   - If the merge is successful, the script proceeds to build the following images:
     - **Safemode Image**
     - **Runmode Image**

5. **Install Images on the RT Target**:
   - The safemode and runmode images are installed on a RT target via SSH.
   - The script then verifies the installation by running tests on the RT target (such as checking the OS version ).

6. **Push Changes and Create Pull Requests**:
   - If the build and test steps succeed, the script commits and pushes the new changes to the downstream fork repository and automatically creates a PR targeting the main branch.

---

## **Configuration File: `automation_conf.json`**

The script is user configurable and uses `automation_conf.json` to define various parameters. **All fields are required**, and if a field is not present, `None` will be used as the default value. Below is an explanation of the fields in the configuration file:

- **`nilrt_branch`**:
  The nilrt branch to pull the latest changes from.

- **`meta_nilrt_branch`**:
  The meta-nilrt branch to pull the latest changes from.

- **`conf_file_path`**:
  Path to the configuration file (default: [`repos.conf`](./repos.conf)).

- **`force_checkout`**:
  Enables forceful checkout to the base branch if set to `True`.

- **`upstream_repo_name`**:
  The name of the upstream remote repository.

- **`merge_branch_name`**:
  The name of the branch where the merge will be performed.

- **`username`**:
  GitHub username where the forks are maintained.

- **`fork_name`**:
  The name of the downstream fork repository where the merge will be performed. This is the repository owned by the user specified in the username field.

- **`email_from`**:
  The email address from which the merge report will be sent.

- **`email_to`**:
  The email address to which the merge report will be sent.

- **`email_log_level`**:
  - **`0`**:
    - Includes the status of the upstream merge:
      - **`... OK`**: Merge completed successfully.
      - **`... OK (no changes)`**: No changes were detected during the merge.
      - **`... ERRORS`**: Errors occurred during the merge.
    - In case of a merge conflict, the error details will also be included in the email.

  - **`1`**:
    - Includes the diff (differences) for a successful merge in addition to the status.

- **`log_level`**:
  Integer representing the logging level:
  - `10`: DEBUG
  - `20`: INFO
  - `30`: WARNING
  - `40`: ERROR
  - `50`: CRITICAL

- **`build_args`**:
  String of extra arguments to pass to the build process (e.g., `"--org"` for NI corporate network builds).

- **`rt_target_IP`**:
  The IP address or hostname of the RT target where images will be installed and tested via SSH.

**`Note`**:
- If the configuration file is `automation_conf.json`, you do not need to specify its path explicitly, as it is set as default. However, if you are using a different configuration file, you must provide its path using the `-c` argument.
For example:

```bash
python3 scripts/dev/upstream_merge/upstream_merge_and_test.py -c path/to/your_config.json -w workItemID
```


---

# HOW TO USE THE MERGE SCRIPT

### **1. Navigate to the root of the nilrt repo**
```bash
cd ~/nilrt
```

### **2. Run the Script**
#### **To Perform a Merge**
This will merge upstream changes, build the images, test them on the RT target, and create PRs with the new changes after the build and test steps succeed.

Note that these steps are serial. The build should succeed for the test to run, and the test should pass for the PRs to be created.

```bash
python3 scripts/dev/upstream_merge/upstream_merge_and_test.py -c path/to/your_config.json -w workItemID
```

- **`workItemID`**:
The `workItemID` associated with the pull request.


#### **To Skip the Merge and Only Build, Test, and Create PRs**

Enable this option when a merge conflict has occurred and you have resolved it manually.
This option is used to skip the automated upstream merge step in the pipeline, allowing the build and test stages to proceed with your manually resolved state.

**How to Manually Resolve a Merge Conflict:**

Once you have resolved the conflict and committed the changes on the build machine, you can rerun the script with the `-s` option to skip the automated merge and proceed directly to the build and test stages.

```bash
python3 scripts/dev/upstream_merge/upstream_merge_and_test.py -c path/to/your_config.json -w workItemID -s
```
#### **To Skip Pushing the Changes and Creating PRs**

Enable this option if you want to run the merge, build, and test steps, but do **not** want to push any changes or create pull requests. This can be useful for dry runs, debugging, or when you want to verify the process without affecting the remote repository.

To use this option, pass the `-skip_push_and_pr` flag when running the script:

```bash
python3 scripts/dev/upstream_merge/upstream_merge_and_test.py -c path/to/your_config.json -w workItemID -skip_push_and_pr
```

---

## **Supporting Files**

### **`shell_commands.py`**
- Provides utility functions to execute shell commands.
- Acts as a wrapper for running system commands from Python.

### **`git_commands.py`**
- Contains various Git-related functions that rely on `shell_commands.py`.
- Includes operations like fetching, pulling, creating branches, and merging.

### **`git_repo.py`**
- Defines the `git_repo` class, which encapsulates details and operations for a Git repository.
-  Data members are:
    - local_repo
    - local_base_branch
    - upstream_branch
    - upstream_repo_name
    - upstream_repo_url
    - fork_name
    - fork_url

### **`upstream_merge.py`**
- Contains helper functions for merging submodules with their respective upstream repositories.

### **`build.py`**
- Handles the process of building images.
- Key steps include:
  - Setting up the Docker environment.
  - Building core feeds.
  - Building core images.

### **`test.py`**
- Manages testing of the built images on an RT target via SSH.
- Key steps include:
  - Installing and testing safemode and runmode images.
  - Verifying the OS version.

### **`push_branch_and_create_pr.py`**
- Handles pushing the merged changes to the downstream fork repository.
- Automates the creation of a pull request on GitHub after a successful merge and build.
- Uses the GitHub CLI or API to generate PRs with appropriate titles, descriptions, and checklists.

> **Important Note:**
> The `push_branch_and_create_pr.py` script performs a **force push** (`git push --force`) to the downstream fork repository.
> This will overwrite the remote branch history and may cause loss of commits if others have pushed to the same branch.
> Use with caution and ensure you coordinate with your team before running this script.

### **`json_config.py`**
- Handles reading and validating the configuration file.
- Key responsibilities include:
  - Parsing the JSON configuration file.
  - Validating required fields and their values.
  - Providing easy access to configuration parameters for other scripts.

### **`log_and_email_utils.py`**
- Provides utilities for logging, formatting merge/build/test reports, and sending email notifications.
- Used by automation scripts to set up logging, format status reports, and send summary emails after merges, builds, and tests.

---

## Contact

If you have any questions or need assistance, feel free to contact:

- Name: Shreejit C
  - GitHub Username: Shreejit-03
  - Email: shreejit.c@emerson.com

- Name: Pratheeksha S N
  - GitHub Username: pratheekshasn
  - Email: pratheeksha.s.n@emerson.com
