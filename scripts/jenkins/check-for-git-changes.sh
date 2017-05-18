#!/bin/bash

set -e -o pipefail

echo ===== Fetch latest changes from origin =====
git fetch --all

echo ====== Set HEAD to the commit @ remotes $BRANCH =====
git checkout -fq `git rev-parse origin/$BRANCH`

echo ===== Clean workspace =====
git clean -ffd

echo ===== Update submodules to latest remotes =====
git submodule init
git submodule update --remote --checkout
git add .

echo ===== Check for changes, create autoci commit, push =====
git add .
if [ "`git diff --name-only "$CIBRANCH" | head -1 `" ]; then
   new_tree=`git write-tree`
   new_commit=`echo "Changes detected, triggering build" | git commit-tree $new_tree -p $CIBRANCH -p origin/$BRANCH`
   git update-ref "refs/heads/$CIBRANCH" $new_commit
   git push origin "$CIBRANCH"
fi

echo ===== Checkout polled commit =====
git checkout -fq "`git rev-parse $CIBRANCH`"
