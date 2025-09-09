#!/bin/bash
set -Eeuo pipefail

user_id=${1:-0}  # default 0 (root)
group_id=${2:-0}  # default 0 (root)

# C++
## Judge version 2023-01
docker build -q ./dockerfiles -t ale-bench:cpp17-202301 -f ./dockerfiles/Dockerfile_cpp17_202301 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:cpp20-202301 -f ./dockerfiles/Dockerfile_cpp20_202301 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:cpp23-202301 -f ./dockerfiles/Dockerfile_cpp23_202301 --build-arg UID=$user_id --build-arg GID=$group_id

# Python
## Judge version 2023-01
docker build -q ./dockerfiles -t ale-bench:python-202301 -f ./dockerfiles/Dockerfile_python_202301 --build-arg UID=$user_id --build-arg GID=$group_id

# Rust
## Judge version 2023-01
docker build -q ./dockerfiles -t ale-bench:rust-202301 -f ./dockerfiles/Dockerfile_rust_202301 --build-arg UID=$user_id --build-arg GID=$group_id
