# MOTIVATION

Maintaining the NI Linux Real-Time kernel on the latest Stable-RT releases is critical for ensuring long-term platform stability, security, performance, and compatibility with upstream Linux developments. Traditionally, upgrading the kernel to a newer Stable-RT release required a series of manual tasks, including identifying the latest RT tag, merging upstream changes, resolving conflicts, preparing the toolchain, building the kernel, deploying it to target hardware, validating successful boot, rebuilding out-of-tree drivers, creating pull requests, and generating status reports.

As Stable-RT releases become more frequent and the kernel continues to evolve, this manual process becomes increasingly time-consuming and error-prone. A single upgrade cycle can require several hours of engineering effort and may involve repetitive validation activities across multiple systems.

To reduce maintenance overhead and improve reliability, the Stable-RT Kernel Upgrade Automation pipeline was developed. The automation transforms the kernel upgrade process into a repeatable, end-to-end workflow that performs the merge, build, deployment, validation, driver verification, and pull request creation with minimal manual intervention.

The script performs the following tasks:

- Automatically clones and prepares the NI Linux kernel repository.
- Fetches and identifies the latest Stable-RT tag corresponding to the target kernel version.
- Merges the latest Stable-RT release into the selected NILRT kernel branch.
- Detects merge conflicts and generates detailed reports to assist with conflict resolution.
- Copies and prepares the required toolchain from the build infrastructure.
- Regenerates kernel configuration files when upstream changes require defconfig updates.
- Builds the kernel image and kernel modules.
- Installs the newly built kernel on a NI Linux Real-Time target system through SSH.
- Reboots the target and verifies that the expected kernel version is running successfully.
- Rebuilds and validates NI out-of-tree drivers using DKMS.
- Pushes the upgrade branch to a GitHub fork and automatically creates a pull request.
- Generates email reports containing merge, build, installation, and validation results.

Overall, this automation significantly reduces manual effort, improves consistency across kernel upgrade activities, accelerates Stable-RT adoption, and ensures that every upgrade undergoes the same build, deployment, and validation process before being submitted for review. By automating the complete kernel integration workflow, the solution improves engineering productivity while increasing confidence in the quality and reliability of Stable-RT kernel upgrades.

---

# SCRIPT OVERVIEW

## Workflow for Stable-RT Kernel Upgrade Automation

The automation performs an end-to-end Stable-RT kernel upgrade, validation, and pull request creation workflow. The objective is to ensure that every Stable-RT upgrade follows a consistent and fully validated process before being submitted for review.

### 1. Setup Passwordless SSH

Before performing any build or deployment activities, the script establishes passwordless SSH communication between the build machine and the target system.

Key activities include:

- Refreshing stale SSH host entries.
- Creating SSH keys on the target if they do not already exist.
- Configuring authorized keys on the build machine.
- Verifying target-to-build-machine connectivity.
- Enabling non-interactive communication required by deployment and validation stages.

This ensures that all subsequent operations can be executed without manual intervention.

### 2. Clone and Prepare the Kernel Repository

The script clones the NI Linux kernel repository and prepares a clean workspace for the upgrade.

Key activities include:

- Cloning the kernel repository.
- Fetching the latest changes from the origin remote.
- Checking out the target NILRT kernel branch.
- Creating a dedicated working branch for the upgrade.

Example:

```text
Target Branch:
nilrt/master/6.18

Working Branch:
rt-merge-6.18

---

# CONFIGURATION FILE: `automation_conf.json`

The Stable-RT Kernel Upgrade Automation script is fully configurable through the `automation_conf.json` file. This file defines the repository configuration, target deployment settings, build environment, reporting configuration, and GitHub integration required for the automation workflow.

All fields are required unless otherwise specified. Missing values may cause the automation to fail during execution.

## Configuration Fields

### `target_branch`

The NILRT kernel branch that will receive the Stable-RT upgrade.

Example:

```text
nilrt/master/6.18
```

### `kernel_src_dir`

Directory where the kernel repository will be cloned and built.

Example:

```text
/home/user/kernel-build/linux
```

### `arch`

Target architecture used for kernel build operations.

Example:

```text
x86_64
```

### `ssh_target`

SSH connection string for the NI Linux Real-Time target system.

Example:

```text
admin@10.152.x.x
```

The target is used for:

- Kernel installation
- Reboot validation
- Runtime testing
- DKMS driver validation

### `ssh_options`

Optional SSH arguments used when communicating with the target.

Example:

```text
-o StrictHostKeyChecking=no
```

### `build_host_ip`

IP address of the build machine.

This value is used when the target mounts the kernel source tree from the build machine using SSHFS during DKMS validation.

Example:

```text
10.152.x.x
```

### `build_host_user`

Username used by the target when accessing the build machine.

Example:

```text
jatin
```

### `username`

GitHub username that owns the fork repository where upgrade branches will be pushed.

Example:

```text
jatinjb444
```

### `fork_name`

Name of the Git remote corresponding to the user's GitHub fork.

Example:

```text
myfork
```

### `email_from`

Email address used as the sender for automation reports.

Example:

```text
automation@company.com
```

### `email_to`

Email address that receives merge, build, and validation reports.

Example:

```text
user@company.com
```

### `log_level`

Logging verbosity level.

Supported values:

```text
10  -> DEBUG
20  -> INFO
30  -> WARNING
40  -> ERROR
50  -> CRITICAL
```

---

## Example Configuration

```json
{
    "username": "jatinjb444",
    "fork_name": "myfork",
    "email_from": "automation@company.com",
    "email_to": "user@company.com",

    "kernel_build": {
        "target_branch": "nilrt/master/6.18",
        "kernel_src_dir": "/home/user/kernel-build/linux",
        "arch": "x86_64",
        "ssh_target": "admin@10.152.x.x",
        "ssh_options": "-o StrictHostKeyChecking=no",
        "build_host_user": "jatin",
        "build_host_ip": "10.152.x.x"
    }
}

```

---

# HOW TO USE THE SCRIPT

## 1. Navigate to the Automation Repository

```bash
cd ~/automation
```

---

## 2. Run the Stable-RT Upgrade Automation

### Perform Complete Stable-RT Upgrade

This is the standard workflow.

The automation will:

- Clone the kernel repository.
- Fetch the latest Stable-RT release.
- Merge the latest RT tag.
- Prepare the toolchain.
- Build the kernel.
- Install the kernel on the target.
- Reboot and validate the target.
- Rebuild DKMS drivers.
- Push the branch.
- Create a GitHub pull request.
- Send the final report.

```bash
python3 scripts/dev/upstream_merge/kernel_build_and_test.py
```

---

### Run Using a Custom Configuration File

```bash
python3 scripts/dev/upstream_merge/kernel_build_and_test.py \
    --config path/to/automation_conf.json
```

---

### Skip Merge Stage

Use this option after manually resolving merge conflicts.

The script skips the Stable-RT merge and continues with:

- Build validation
- Kernel installation
- Boot verification
- DKMS validation
- Pull request creation

```bash
python3 scripts/dev/upstream_merge/kernel_build_and_test.py \
    --skip-merge
```

---

### Skip Push and Pull Request Creation

Useful when validating the upgrade without modifying GitHub repositories.

The automation will:

- Merge
- Build
- Install
- Validate
- Rebuild DKMS

but will not:

- Push branches
- Create pull requests

```bash
python3 scripts/dev/upstream_merge/kernel_build_and_test.py \
    --skip-push-and-pr
```

---

### Use a Custom Workspace

Specify a custom build directory.

```bash
python3 scripts/dev/upstream_merge/kernel_build_and_test.py \
    --work-dir /tmp/kernel-build
```

---

## Merge Conflict Handling

If a Stable-RT merge introduces conflicts, the automation immediately stops and generates a report.

Example:

```text
CONFLICT (content):
arch/arm/mm/fault.c
```

In this situation:

1. Resolve the merge conflict manually.
2. Commit the conflict resolution.
3. Rerun the script using:

```bash
python3 scripts/dev/upstream_merge/kernel_build_and_test.py \
    --skip-merge
```

This allows the automation to continue with build, installation, validation, and pull request creation without repeating the merge operation.

---

## Failure Handling

The automation follows a fail-fast strategy.

Examples:

- Merge failure → Build skipped
- Build failure → Installation skipped
- Installation failure → Validation skipped
- Validation failure → PR creation skipped

This prevents invalid upgrades from progressing through later stages.

---

## Generated Outputs

A successful execution produces:

- Stable-RT merge commit
- Built kernel image
- Installed kernel on target
- Kernel version validation
- DKMS rebuild results
- GitHub branch
- GitHub pull request
- Build and validation reports

All execution results are included in the final email report.

---

# SUPPORTING FILES

### `kernel_build_and_test.py`

Main entry point for the Stable-RT Kernel Upgrade Automation.

Responsibilities:

- Parse command line arguments.
- Load configuration.
- Setup build environment.
- Perform Stable-RT merge.
- Trigger build and deployment workflows.
- Validate upgraded kernel.
- Create pull requests.
- Generate reports.

---

### `git_commands.py`

Provides utility functions for common Git operations.

Supported operations include:

- Repository cloning
- Fetching remotes
- Branch creation
- Branch checkout
- Merging
- Commit creation
- Push operations
- Pull request creation
- Repository status retrieval

This file acts as the primary Git abstraction layer for the automation.

---

### `git_repo.py`

Defines the `GitRepo` class used throughout the automation.

Key responsibilities:

- Repository metadata management
- Remote management
- Branch configuration
- Fork configuration
- Git operation abstraction

Important data members include:

- `local_repo`
- `local_base_branch`
- `upstream_branch`
- `upstream_repo_name`
- `upstream_repo_url`
- `fork_name`
- `fork_url`

---

### `shell_commands.py`

Utility module responsible for executing system commands.

Responsibilities:

- Running shell commands
- Capturing command output
- Returning exit codes
- Logging command execution details

Most lower-level operations eventually execute through this module.

---

### `json_config.py`

Handles configuration management.

Responsibilities include:

- Reading configuration files
- Validating configuration values
- Providing configuration access across modules
- Managing default values

The automation relies on this module to initialize runtime settings.

---

### `build.py`

Handles kernel build and configuration validation operations.

Key activities include:

- Toolchain configuration
- Kernel compilation
- Module compilation
- Defconfig regeneration
- Build validation

Important functions include:

- `build_kernel_x86_64()`
- `regenerate_defconfig()`

---

### `copy_toolchain_from_server.py`

Responsible for toolchain preparation.

Key activities include:

- Copying approved toolchains from build infrastructure
- Preparing environment variables
- Validating toolchain availability

Important functions include:

- `copy_toolchain_from_nirvana()`
- `prepare_toolchain_environment()`

---

### `rebuild_drivers.py`

Handles DKMS validation following kernel installation.

Key activities include:

- Installing SSHFS dependencies
- Mounting kernel sources
- Updating build/source links
- Preparing kernel headers
- Rebuilding DKMS drivers

Important functions include:

- `install_sshfs_fuse()`
- `mount_kernel_source()`
- `fix_symlinks()`
- `prepare_headers()`
- `dkms_autoinstall()`

---

### `push_branch_and_create_pr.py`

Handles GitHub integration.

Key activities include:

- Branch publication
- Fork management
- Pull request creation
- PR description generation

The module automatically publishes validated Stable-RT upgrades to GitHub.

> **Important Note:**
>
> This workflow may perform force-push operations depending on the selected branch strategy.
>
> Ensure no other users are modifying the same automation branch before execution.

---

### `log_and_email_utils.py`

Provides logging and email reporting functionality.

Responsibilities include:

- Log initialization
- Status report generation
- Email formatting
- Failure reporting
- Success notifications

Reports include:

- Merge status
- Build status
- Install status
- Boot validation status
- DKMS validation status
- Pull request information

---

### `install_kernel_to_target()`

Responsible for deploying the newly built kernel to the NI Linux Real-Time target.

Deployment activities include:

- Backing up the existing kernel
- Copying the new kernel image
- Copying kernel modules
- Running depmod
- Updating boot symlinks
- Configuring recovery boot delay
- Rebooting the target

The automation verifies all deployment steps before rebooting the target.

---

### `wait_for_ssh()`

Used during reboot validation.

Responsibilities include:

- Waiting for target reboot completion
- Verifying SSH accessibility
- Allowing post-install validation to continue only after the target becomes reachable

---

### `setup_passwordless_ssh_to_build_machine()`

Establishes passwordless SSH communication.

Responsibilities include:

- Refreshing known_hosts entries
- Generating SSH credentials when necessary
- Configuring authorized_keys
- Verifying target-to-build-machine connectivity

This functionality is required for SSHFS-based source mounting during DKMS validation.

# CONTACT

If you have any questions, issues, or enhancement requests regarding the Stable-RT Kernel Upgrade Automation, please contact:

- Name: Jatin Bharti
- GitHub Username: jatinjb444
- Team: NI RTOS
- Email: jatin.bharti@emerson.com