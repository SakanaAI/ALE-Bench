#!/bin/bash
set -Eeuo pipefail

remote=${1:-"yimjk/ale-bench"}

docker image push ${remote}:cpp17-201907
docker image push ${remote}:cpp17-202301
docker image push ${remote}:cpp20-202301
docker image push ${remote}:cpp23-202301
docker image push ${remote}:python-201907
docker image push ${remote}:python-202301
docker image push ${remote}:rust-201907
docker image push ${remote}:rust-202301
