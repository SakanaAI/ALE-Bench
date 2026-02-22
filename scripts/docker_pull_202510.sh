#!/bin/bash
set -Eeuo pipefail

remote=${1:-"yimjk/ale-bench"}

docker image pull ${remote}:bash-202510
docker image pull ${remote}:cpp23-202510
docker image pull ${remote}:csharp-202510
docker image pull ${remote}:fish-202510
docker image pull ${remote}:fortran-202510
docker image pull ${remote}:go-202510
docker image pull ${remote}:haskell-202510
docker image pull ${remote}:javascript-202510
docker image pull ${remote}:julia-202510
docker image pull ${remote}:lean-202510
docker image pull ${remote}:ocaml-202510
docker image pull ${remote}:perl-202510
docker image pull ${remote}:pypy-202510
docker image pull ${remote}:python-202510
docker image pull ${remote}:rust-202510
docker image pull ${remote}:typescript-202510
docker image pull ${remote}:all-202510
docker image pull ${remote}:all-lean-202510
