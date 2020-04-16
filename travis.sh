#!/usr/bin/env bash

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
TOKEN=$(curl -s -H "Content-Type: application/json" -X POST -d "
{
\"username\": \"$DOCKER_USERNAME\",
\"password\": \"$DOCKER_PASSWORD\"
}
" https://hub.docker.com/v2/users/login/ | jq -r .token)

DOCKER_TAG=`git name-rev --tags --name-only $(git rev-parse HEAD)`
if []${DOCKER_TAG} != "undefined"]
then
  echo "docker build -t xebialabsunsupported/slack-xlrelease-app:${DOCKER_TAG} ."
  echo "docker push xebialabsunsupported/slack-xlrelease-app:${DOCKER_TAG}"
fi
echo "docker build -t xebialabsunsupported/slack-xlrelease-app:latest ."
echo "docker push xebialabsunsupported/slack-xlrelease-app:latest"
