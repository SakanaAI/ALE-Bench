#!/bin/bash
set -Eeuo pipefail

repo=${1:-"ale-bench"}

docker rmi ${repo}:cpp17-201907
docker rmi ${repo}:cpp17-202301
docker rmi ${repo}:cpp20-202301
docker rmi ${repo}:cpp23-202301
docker rmi ${repo}:python-201907
docker rmi ${repo}:python-202301
docker rmi ${repo}:rust-201907
docker rmi ${repo}:rust-202301
