#!/bin/bash
set -Eeuo pipefail

repo=${1:-"ale-bench"}

docker rmi ${repo}:bash-202510
docker rmi ${repo}:cpp23-202510
docker rmi ${repo}:csharp-202510
docker rmi ${repo}:fish-202510
docker rmi ${repo}:fortran-202510
docker rmi ${repo}:go-202510
docker rmi ${repo}:haskell-202510
docker rmi ${repo}:javascript-202510
docker rmi ${repo}:julia-202510
docker rmi ${repo}:lean-202510
docker rmi ${repo}:ocaml-202510
docker rmi ${repo}:perl-202510
docker rmi ${repo}:pypy-202510
docker rmi ${repo}:python-202510
docker rmi ${repo}:rust-202510
docker rmi ${repo}:typescript-202510
docker rmi ${repo}:all-202510
docker rmi ${repo}:all-lean-202510
