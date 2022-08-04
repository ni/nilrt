#!/bin/bash

# This script can be used for merging latest upstream for each of the
# repos described in repos.conf
#
# For each local repo, it does following
# 1. Check if local_base_branch specified in repos.conf exists
# 2. Checkout local_base_branch and run git pull
# 3. Add a 'remote' named 'automerge_upstream'
#    a. If the remote already exists, remove it first
# 4. Fetches remote branch
# 5. Creates a branch named 'dev/automerge/ni' from 'nilrt/master/hardknott' and checkout
#    a. If the branch name exists, ask to delete or skip or cancel
# 6. Merges 'automerge_upstream/$LOCAL_BRANCH_NAME' into 'dev/automerge/ni'
#    a. Success or failure is reported; script continues in either case

DIR=$(dirname ${BASH_SOURCE})
CONF_FILE="$DIR/repos.conf"

REMOTE_REPO_NAME="automerge_upstream"
LOCAL_BRANCH_NAME="dev/automerge/ni"

usage() {
   echo "Usage: $0 [-c <conf file>][-h] " 1>&2
}

parse_args() {
   local OPTIND o

   while getopts "c:h" o; do
      case "${o}" in
         c)
            CONF_FILE=${OPTARG}
            ;;
         h)
            usage
            exit 0
            ;;
         *)
            usage
            exit 1
            ;;
      esac
   done
   shift $((OPTIND-1))
}

sanity_test_repo() {
   local LOCAL_BASE_BRANCH=$1

   if ! $(git rev-parse --verify $LOCAL_BASE_BRANCH &> /dev/null); then
      echo ""
      echo "    Branch $LOCAL_BASE_BRANCH does not exist. Exiting"
      exit 1
   fi
}

update_local_base_branch() {
   local LOCAL_BASE_BRANCH=$1

   if $(git checkout $LOCAL_BASE_BRANCH &> /dev/null); then
      if ! $(git pull &> /dev/null); then
         echo ""
         echo "    Error pulling latest on $LOCAL_BASE_BRANCH. Exiting"
         exit 1
      fi
   else
      # Error changing branch
      echo ""
      echo "    Error switching to branch $LOCAL_BASE_BRANCH. Exiting"
      exit 1
   fi
}

add_remote() {
   local UPSTREAM_REPO=$1

   git remote remove $REMOTE_REPO_NAME &> /dev/null || true
   git remote add $REMOTE_REPO_NAME $UPSTREAM_REPO
}

fetch_remote_branch() {
   local UPSTREAM_BRANCH=$1

   if ! $(git fetch $REMOTE_REPO_NAME $UPSTREAM_BRANCH &> /dev/null); then
         echo ""
         echo "    Error fetching $UPSTREAM_BRANCH from $REMOTE_REPO_NAME. Exiting"
         exit 1
   fi
}

# Returns 1 if repo should be skipped, 0 if not
handle_existing_local_branch() {
   local LOCAL_BASE_BRANCH=$1

   while true; do
      echo ""
      echo "    Branch $LOCAL_BRANCH_NAME already exists"
      read -p "    Delete Branch(d)/Skip Repo(s)/Cancel Merge(c)? " dsc
      case $dsc in
         [d]* )
            if ! $(git checkout $LOCAL_BASE_BRANCH &> /dev/null); then
               echo ""
               echo "    Error switching to branch $LOCAL_BASE_BRANCH. Exiting"
               exit 1
            fi
            git branch -D $LOCAL_BRANCH_NAME &> /dev/null;
            return 0;;
         [s]* ) return 1;;
         [c]* ) echo "Exiting"; exit;;
         * ) echo "    Please answer d/s/c";;
      esac
   done < /dev/stdin
}

# Returns 1 if repo should be skipped, 0 if not
create_local_branch() {
   local LOCAL_BASE_BRANCH=$1

   if $(git rev-parse --verify $LOCAL_BRANCH_NAME &> /dev/null); then
      # Branch already exists
      if ! handle_existing_local_branch $LOCAL_BASE_BRANCH; then
         return 1 # Skip repo
      fi
   fi
   if ! $(git checkout -b $LOCAL_BRANCH_NAME $LOCAL_BASE_BRANCH &> /dev/null); then
      echo ""
      echo "    Error creating $LOCAL_BRANCH_NAME. Exiting"
      exit 1
   fi
   return 0
}

# Returns 0 if non empty merge and 1 for empty/no merge
is_non_empty_merge() {
   local COMMIT_BEFORE_MERGE=$1
   local COMMIT_AFTER_MERGE=$(git rev-parse HEAD)

   if [ "$COMMIT_BEFORE_MERGE" == "$COMMIT_AFTER_MERGE" ]; then
      # No merge commit
      return 1
   fi

   if $(git diff HEAD~1 HEAD | grep diff &> /dev/null); then
      # Non empty merge commit
      return 0
   fi
   # Empty merge commit
   # This can occur when upstream was previously merged with a squash commit
   return 1
}

merge_upstream_branch() {
   local UPSTREAM_BRANCH=$1

   local COMMIT_BEFORE_MERGE=$(git rev-parse HEAD)

   if $(git merge $REMOTE_REPO_NAME/$UPSTREAM_BRANCH --signoff -m "Merge latest upstream" &> /dev/null); then
      if is_non_empty_merge $COMMIT_BEFORE_MERGE; then
         echo " ... OK"
      else
         echo " ... OK (no changes)"
      fi
   else
      echo " ... ERRORS"
   fi
}

handle_repo() {
   local LOCAL_REPO=$1
   local UPSTREAM_REPO=$2
   local UPSTREAM_BRANCH=$3
   local LOCAL_BASE_BRANCH=$4

   pushd $LOCAL_REPO &> /dev/null
   echo -n $LOCAL_REPO

   sanity_test_repo $LOCAL_BASE_BRANCH
   update_local_base_branch $LOCAL_BASE_BRANCH
   add_remote $UPSTREAM_REPO
   fetch_remote_branch $UPSTREAM_BRANCH
   if ! create_local_branch $LOCAL_BASE_BRANCH; then
      echo " ... SKIPPED"
   else
      merge_upstream_branch $UPSTREAM_BRANCH
   fi

   popd &> /dev/null
}

main() {
   while read -u 10 line; do
      if [[ "$line" =~ ^#.* ]]; then
         continue
      fi

      local LOCAL_REPO=$(echo $line | awk '{print $1}')
      local UPSTREAM_REPO=$(echo $line | awk '{print $2}')
      local UPSTREAM_BRANCH=$(echo $line | awk '{print $3}')
      local LOCAL_BASE_BRANCH=$(echo $line | awk '{print $4}')

      handle_repo $LOCAL_REPO $UPSTREAM_REPO $UPSTREAM_BRANCH $LOCAL_BASE_BRANCH
   done 10< $CONF_FILE
}

parse_args "$@"
main
