#!/bin/bash
set -e

image_tag="$1"

jenkins_uid=$(id -u)
jenkins_gid=$(id -g)
jenkins_user=$(id -un)
jenkins_group=$(id -gn)

sed -e "s/#JENKINS_UID#/$jenkins_uid/g" \
    -e "s/#JENKINS_GID#/$jenkins_gid/g" \
    -e "s/#JENKINS_USER#/$jenkins_user/g" \
    -e "s/#JENKINS_GROUP#/$jenkins_group/g" \
    scripts/jenkins/Dockerfile.template > scripts/jenkins/Dockerfile

docker build --no-cache=true --squash -f scripts/jenkins/Dockerfile -t "$image_tag" scripts/jenkins

rm -f scripts/jenkins/Dockerfile

docker container prune -f
docker image prune -f
