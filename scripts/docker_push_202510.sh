#!/bin/bash
set -Eeuo pipefail

remote=${1:-"yimjk/ale-bench"}

docker image push ${remote}:bash-202510
docker image push ${remote}:cpp23-202510
docker image push ${remote}:csharp-202510
docker image push ${remote}:fish-202510
docker image push ${remote}:fortran-202510
docker image push ${remote}:go-202510
docker image push ${remote}:haskell-202510
docker image push ${remote}:javascript-202510
docker image push ${remote}:julia-202510
docker image push ${remote}:lean-202510
docker image push ${remote}:ocaml-202510
docker image push ${remote}:perl-202510
docker image push ${remote}:pypy-202510
docker image push ${remote}:python-202510
docker image push ${remote}:rust-202510
docker image push ${remote}:typescript-202510
docker image push ${remote}:all-202510
docker image push ${remote}:all-lean-202510
