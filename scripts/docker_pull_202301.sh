#!/bin/bash
set -Eeuo pipefail

remote=${1:-"yimjk/ale-bench"}

docker image pull ${remote}:cpp17-202301
docker image pull ${remote}:cpp20-202301
docker image pull ${remote}:cpp23-202301
docker image pull ${remote}:python-202301
docker image pull ${remote}:rust-202301
