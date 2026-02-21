#!/bin/bash
set -Eeuo pipefail

user_id=${1:-0}  # default 0 (root)
group_id=${2:-0}  # default 0 (root)

# Build local runnable images from prebuilt 2025-10 base images

docker build -q ./dockerfiles -t ale-bench:bash-202510 -f ./dockerfiles/Dockerfile_bash_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:cpp23-202510 -f ./dockerfiles/Dockerfile_cpp23_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:csharp-202510 -f ./dockerfiles/Dockerfile_csharp_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:fish-202510 -f ./dockerfiles/Dockerfile_fish_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:fortran-202510 -f ./dockerfiles/Dockerfile_fortran_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:go-202510 -f ./dockerfiles/Dockerfile_go_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:haskell-202510 -f ./dockerfiles/Dockerfile_haskell_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:javascript-202510 -f ./dockerfiles/Dockerfile_javascript_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:julia-202510 -f ./dockerfiles/Dockerfile_julia_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:lean-202510 -f ./dockerfiles/Dockerfile_lean_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:ocaml-202510 -f ./dockerfiles/Dockerfile_ocaml_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:perl-202510 -f ./dockerfiles/Dockerfile_perl_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:pypy-202510 -f ./dockerfiles/Dockerfile_pypy_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:python-202510 -f ./dockerfiles/Dockerfile_python_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:rust-202510 -f ./dockerfiles/Dockerfile_rust_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:typescript-202510 -f ./dockerfiles/Dockerfile_typescript_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:all-202510 -f ./dockerfiles/Dockerfile_all_202510 --build-arg UID=$user_id --build-arg GID=$group_id
docker build -q ./dockerfiles -t ale-bench:all-lean-202510 -f ./dockerfiles/Dockerfile_all_lean_202510 --build-arg UID=$user_id --build-arg GID=$group_id
