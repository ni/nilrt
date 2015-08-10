#!/bin/sh
#
# This script is meant to be run inside 'git foreach'.
#
# Returns the name of the current submodule ($name) if commits have been made to
# the remote (upstream) branch that have not been applied to the local branch.
# The name of the remote branch is obtained from .gitmodules. The name of the
# remote is assumed to be "origin".

parentdir=$(cd .. && git rev-parse --show-toplevel)

# Get the name of the remote branch we're (nominally) tracking
remotebranch=$(git config -f "$parentdir"/.gitmodules submodule.$name.branch \
	|| echo master)

# Fetch the remote id (the commit id of the remote branch)
remoteid=$(git ls-remote --exit-code origin refs/heads/$remotebranch \
	|| echo FAIL)
remoteid=$(echo $remoteid | cut -f1 -d\  )

# Get the local id (commit id of HEAD)
localid=$(cd "$parentdir" && git ls-files --stage $path | cut -f2 -d\  )

# Find the most recent common ancestor of the remote and local commits
mergeid=$(git merge-base $remoteid $localid || echo FAIL)

# If the merge and remote ids are the same then the local id is at least as
# young and we don't need to update. Otherwise, we do need to update.
[ "$remoteid" != FAIL -a "$localid" != FAIL -a "$mergeid" != FAIL -a \
	"$mergeid" = "$remoteid" ] || echo $name
