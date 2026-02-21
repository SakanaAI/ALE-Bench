#!/bin/bash
set -Eeuo pipefail

# Build AtCoder 2025-10 base images (publish target tags)

docker build -q ./dockerfiles -t yimjk/ale-bench:bash-202510 -f ./dockerfiles/Dockerfile_bash_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:cpp23-202510 -f ./dockerfiles/Dockerfile_cpp23_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:csharp-202510 -f ./dockerfiles/Dockerfile_csharp_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:fish-202510 -f ./dockerfiles/Dockerfile_fish_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:fortran-202510 -f ./dockerfiles/Dockerfile_fortran_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:go-202510 -f ./dockerfiles/Dockerfile_go_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:haskell-202510 -f ./dockerfiles/Dockerfile_haskell_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:javascript-202510 -f ./dockerfiles/Dockerfile_javascript_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:julia-202510 -f ./dockerfiles/Dockerfile_julia_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:lean-202510 -f ./dockerfiles/Dockerfile_lean_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:ocaml-202510 -f ./dockerfiles/Dockerfile_ocaml_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:perl-202510 -f ./dockerfiles/Dockerfile_perl_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:pypy-202510 -f ./dockerfiles/Dockerfile_pypy_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:python-202510 -f ./dockerfiles/Dockerfile_python_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:rust-202510 -f ./dockerfiles/Dockerfile_rust_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:typescript-202510 -f ./dockerfiles/Dockerfile_typescript_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:all-202510 -f ./dockerfiles/Dockerfile_all_202510_base
docker build -q ./dockerfiles -t yimjk/ale-bench:all-lean-202510 -f ./dockerfiles/Dockerfile_all_lean_202510_base
