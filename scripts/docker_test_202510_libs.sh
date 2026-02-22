#!/bin/bash
set -Eeuo pipefail

usage() {
    cat <<'USAGE'
Usage:
  scripts/docker_test_202510_libs.sh [options]

Options:
  --image-prefix <PREFIX>   Docker image prefix (default: auto-detect)
  --tag <TAG>               Image tag suffix (default: 202510)
  --langs <CSV>             Comma-separated languages to test
  --heavy-seconds <N>       Heavy workload duration in seconds (default: 2)
  --uid, -u <UID>           User ID for docker run (default: 0)
  --gid, -g <GID>           Group ID for docker run (default: 0)
  --quiet, -q               Suppress stderr on success
  --list                    Show supported languages and exit
  -h, --help                Show this help

Examples:
  scripts/docker_test_202510_libs.sh
  scripts/docker_test_202510_libs.sh --image-prefix yimjk/ale-bench --tag 202510
  scripts/docker_test_202510_libs.sh --langs cpp23,rust,python
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEST_ROOT="${REPO_ROOT}/dockerfiles/tests"

SUPPORTED_LANGS=(
    bash
    cpp23
    csharp
    fish
    fortran
    go
    haskell
    javascript
    julia
    lean
    ocaml
    perl
    pypy
    python
    rust
    typescript
)

IMAGE_PREFIX=""
TAG="202510"
HEAVY_SECONDS="2"
QUIET=0
LANGS=("${SUPPORTED_LANGS[@]}")
USER_ID=0
GROUP_ID=0

contains_lang() {
    local target="$1"
    local x
    for x in "${SUPPORTED_LANGS[@]}"; do
        if [[ "${x}" == "${target}" ]]; then
            return 0
        fi
    done
    return 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
    --image-prefix)
        IMAGE_PREFIX="${2:-}"
        shift 2
        ;;
    --tag)
        TAG="${2:-}"
        shift 2
        ;;
    --langs)
        IFS=',' read -r -a LANGS <<<"${2:-}"
        shift 2
        ;;
    --heavy-seconds)
        HEAVY_SECONDS="${2:-}"
        shift 2
        ;;
    -q | --quiet)
        QUIET=1
        shift
        ;;
    --list)
        printf '%s\n' "${SUPPORTED_LANGS[@]}"
        exit 0
        ;;
    -u | --uid)
        USER_ID="${2:-}"
        shift 2
        ;;
    -g | --gid)
        GROUP_ID="${2:-}"
        shift 2
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo "docker command not found" >&2
    exit 1
fi

if [[ ${#LANGS[@]} -eq 0 ]]; then
    echo "No languages specified" >&2
    exit 1
fi

if ! [[ "${HEAVY_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${HEAVY_SECONDS}" -lt 1 ]]; then
    echo "Invalid --heavy-seconds value: ${HEAVY_SECONDS} (must be integer >= 1)" >&2
    exit 1
fi

if ! [[ "${USER_ID}" =~ ^[0-9]+$ ]]; then
    echo "Invalid --uid value: ${USER_ID} (must be integer >= 0)" >&2
    exit 1
fi

if ! [[ "${GROUP_ID}" =~ ^[0-9]+$ ]]; then
    echo "Invalid --gid value: ${GROUP_ID} (must be integer >= 0)" >&2
    exit 1
fi

for lang in "${LANGS[@]}"; do
    if ! contains_lang "${lang}"; then
        echo "Unsupported language: ${lang}" >&2
        exit 1
    fi
done

command_for_lang() {
    case "$1" in
    bash)
        cat <<'CMD'
cp /repo/dockerfiles/tests/bash/Main.bash /workdir/Main.bash
/usr/bin/time -f "[time][bash][compile] real=%e user=%U sys=%S maxrss_kb=%M" bash -n /workdir/Main.bash
/usr/bin/time -f "[time][bash][execute] real=%e user=%U sys=%S maxrss_kb=%M" bash /workdir/Main.bash
CMD
        ;;
    cpp23)
        cat <<'CMD'
export PATH=/opt/gcc-15.2.0/bin:$PATH
export LD_LIBRARY_PATH=/opt/gcc-15.2.0/lib64:/opt/gcc-15.2.0/lib:${LD_LIBRARY_PATH:-}
cp /repo/dockerfiles/tests/cpp23/Main.cpp /workdir/Main.cpp
AC_VARIANT=gcc
USER_BUILD_FLAGS=(
"-DATCODER"
"-DNOMINMAX"
"-DONLINE_JUDGE"
"-DOR_PROTO_DLL="
"-DPROTOBUF_USE_DLLS"
"-DUSE_BOP"
"-DUSE_CBC"
"-DUSE_CLP"
"-DUSE_GLOP"
"-DUSE_LP_PARSER"
"-DUSE_MATH_OPT"
"-DUSE_PDLP"
"-DUSE_SCIP"
"-I/opt/gcc-15.2.0/include"
"-I/opt/gcc-15.2.0/include/torch/csrc/api/include"
"-O2"
"-Wall"
"-Wextra"
"-fconstexpr-depth=1024"
"-fconstexpr-loop-limit=524288"
"-fconstexpr-ops-limit=2097152"
"-flto=auto"
"-fmodules"
"-ftrivial-auto-var-init=zero"
"-march=native"
"-pthread"
"-std=gnu++23"
"-Wl,--as-needed"
"-L/opt/gcc-15.2.0/lib64"
"-Wl,-R/opt/gcc-15.2.0/lib64"
"-L/opt/gcc-15.2.0/lib"
"-Wl,-R/opt/gcc-15.2.0/lib"
"-fopenmp"
"-lstdc++exp"
"-labsl_cordz_sample_token"
"-labsl_failure_signal_handler"
"-labsl_flags_parse"
"-labsl_flags_usage"
"-labsl_flags_usage_internal"
"-labsl_log_flags"
"-labsl_periodic_sampler"
"-labsl_poison"
"-labsl_random_internal_distribution_test_util"
"-labsl_scoped_set_env"
"-lboost_atomic"
"-lboost_charconv"
"-lboost_chrono"
"-lboost_container"
"-lboost_context"
"-lboost_contract"
"-lboost_coroutine"
"-lboost_date_time"
"-lboost_exception"
"-lboost_fiber"
"-lboost_filesystem"
"-lboost_graph"
"-lboost_iostreams"
"-lboost_json"
"-lboost_locale"
"-lboost_log"
"-lboost_log_setup"
"-lboost_math_c99"
"-lboost_math_c99f"
"-lboost_math_c99l"
"-lboost_math_tr1"
"-lboost_math_tr1f"
"-lboost_math_tr1l"
"-lboost_nowide"
"-lboost_prg_exec_monitor"
"-lboost_process"
"-lboost_program_options"
"-lboost_random"
"-lboost_regex"
"-lboost_serialization"
"-lboost_stacktrace_from_exception"
"-lboost_system"
"-lboost_test_exec_monitor"
"-lboost_thread"
"-lboost_timer"
"-lboost_type_erasure"
"-lboost_unit_test_framework"
"-lboost_url"
"-lboost_wave"
"-lboost_wserialization"
"-lgmpxx"
"-lgmp"
"-lortools"
"-lCbc"
"-lCbcSolver"
"-lCgl"
"-lClp"
"-lClpSolver"
"-lCoinUtils"
"-lGLPK"
"-lOsi"
"-lOsiCbc"
"-lOsiClp"
"-lhighs"
"-lscip"
"-lz"
"-lbz2"
"-lprotobuf"
"-labsl_die_if_null"
"-labsl_log_initialize"
"-labsl_random_distributions"
"-labsl_random_seed_sequences"
"-labsl_random_internal_entropy_pool"
"-labsl_random_internal_randen"
"-labsl_random_internal_randen_hwaes"
"-labsl_random_internal_randen_hwaes_impl"
"-labsl_random_internal_randen_slow"
"-labsl_random_internal_platform"
"-labsl_random_internal_seed_material"
"-labsl_random_seed_gen_exception"
"-labsl_statusor"
"-labsl_status"
"-lutf8_validity"
"-lutf8_range"
"-pthread"
"-lre2"
"-labsl_log_internal_check_op"
"-labsl_leak_check"
"-labsl_log_internal_conditions"
"-labsl_log_internal_message"
"-labsl_examine_stack"
"-labsl_log_internal_format"
"-labsl_log_internal_nullguard"
"-labsl_log_internal_structured_proto"
"-labsl_log_internal_proto"
"-labsl_log_internal_log_sink_set"
"-labsl_log_internal_globals"
"-labsl_log_globals"
"-labsl_log_sink"
"-labsl_strerror"
"-labsl_vlog_config_internal"
"-labsl_log_internal_fnmatch"
"-labsl_flags_internal"
"-labsl_flags_marshalling"
"-labsl_flags_reflection"
"-labsl_flags_private_handle_accessor"
"-labsl_flags_commandlineflag"
"-labsl_flags_commandlineflag_internal"
"-labsl_flags_config"
"-labsl_flags_program_name"
"-labsl_raw_hash_set"
"-labsl_cord"
"-labsl_cordz_info"
"-labsl_cord_internal"
"-labsl_cordz_functions"
"-labsl_cordz_handle"
"-labsl_crc_cord_state"
"-labsl_crc32c"
"-labsl_crc_internal"
"-labsl_crc_cpu_detect"
"-labsl_hashtablez_sampler"
"-labsl_exponential_biased"
"-labsl_hash"
"-labsl_city"
"-labsl_low_level_hash"
"-labsl_str_format_internal"
"-labsl_synchronization"
"-labsl_graphcycles_internal"
"-labsl_kernel_timeout_internal"
"-labsl_stacktrace"
"-labsl_symbolize"
"-labsl_debugging_internal"
"-labsl_demangle_internal"
"-labsl_demangle_rust"
"-labsl_decode_rust_punycode"
"-labsl_utf8_for_code_point"
"-labsl_malloc_internal"
"-labsl_time"
"-labsl_civil_time"
"-labsl_strings"
"-labsl_strings_internal"
"-labsl_string_view"
"-labsl_int128"
"-labsl_throw_delegate"
"-labsl_time_zone"
"-labsl_tracing_internal"
"-labsl_base"
"-lrt"
"-labsl_raw_logging_internal"
"-labsl_log_severity"
"-labsl_spinlock_wait"
"-lz3"
"-l_lightgbm"
"-ltorch"
"-ltorch_cpu"
"-lc10")
/usr/bin/time -f "[time][cpp23][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  g++ ./Main.cpp -o a.out "${USER_BUILD_FLAGS[@]}"
/usr/bin/time -f "[time][cpp23][execute] real=%e user=%U sys=%S maxrss_kb=%M" ./a.out
CMD
        ;;
    csharp)
        cat <<'CMD'
export DOTNET_ROOT=/opt/dotnet
export PATH=/opt/dotnet:/opt/dotnet/tools:$PATH
export DOTNET_EnableWriteXorExecute=0
export DOTNET_CLI_TELEMETRY_OPTOUT=1
cp /repo/dockerfiles/tests/csharp/Main.cs /workdir/Main.cs
/usr/bin/time -f "[time][csharp][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  dotnet publish -c Release -o /workdir/publish --no-restore --nologo -v q --tl:off
/usr/bin/time -f "[time][csharp][execute] real=%e user=%U sys=%S maxrss_kb=%M" /workdir/publish/Main
CMD
        ;;
    fish)
        cat <<'CMD'
cp /repo/dockerfiles/tests/fish/Main.fish /workdir/Main.fish
/usr/bin/time -f "[time][fish][compile] real=%e user=%U sys=%S maxrss_kb=%M" fish -n /workdir/Main.fish
/usr/bin/time -f "[time][fish][execute] real=%e user=%U sys=%S maxrss_kb=%M" fish /workdir/Main.fish
CMD
        ;;
    fortran)
        cat <<'CMD'
cp /repo/dockerfiles/tests/fortran/Main.f90 /workdir/Main.f90
/usr/bin/time -f "[time][fortran][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  gfortran-14 -I/workdir -I/usr/local/include -L/usr/local/lib -Wl,-rpath,/usr/local/lib \
  -O2 -cpp -ffree-line-length-none -std=f2023 \
  /workdir/Main.f90 -lstdlib -o /workdir/a.out
/usr/bin/time -f "[time][fortran][execute] real=%e user=%U sys=%S maxrss_kb=%M" /workdir/a.out
CMD
        ;;
    go)
        cat <<'CMD'
export PATH=$PATH:/opt/go/bin
cp /repo/dockerfiles/tests/go/main.go /workdir/main.go
cd /workdir
/usr/bin/time -f "[time][go][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  env GOPROXY=off GO111MODULE=on go build -o a.out main.go
/usr/bin/time -f "[time][go][execute] real=%e user=%U sys=%S maxrss_kb=%M" ./a.out
CMD
        ;;
    haskell)
        cat <<'CMD'
export PATH=/opt/.ghcup/bin:$PATH
cp /repo/dockerfiles/tests/haskell/Main.hs /workdir/submission/app/Main.hs
cd /workdir/submission
/usr/bin/time -f "[time][haskell][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  bash -lc 'cabal v2-build --offline && cp $(cabal list-bin main) /workdir/'
/usr/bin/time -f "[time][haskell][execute] real=%e user=%U sys=%S maxrss_kb=%M" /workdir/main
CMD
        ;;
    javascript)
        cat <<'CMD'
cp /repo/dockerfiles/tests/javascript/Main.js /workdir/Main.js
/usr/bin/time -f "[time][javascript][compile] real=%e user=%U sys=%S maxrss_kb=%M" node --check /workdir/Main.js
/usr/bin/time -f "[time][javascript][execute] real=%e user=%U sys=%S maxrss_kb=%M" \
  /workdir/node.sh 1048576 /workdir/Main.js ONLINE_JUDGE ATCODER
CMD
        ;;
    julia)
        cat <<'CMD'
cp /repo/dockerfiles/tests/julia/Main.jl /workdir/Main.jl
export PATH=$PATH:/workdir/.juliaup/bin
export JULIA_DEPOT_PATH=/workdir/.julia
/usr/bin/time -f "[time][julia][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  julia -e 'Meta.parse("begin " * read("Main.jl",String) * " end")'
/usr/bin/time -f "[time][julia][execute] real=%e user=%U sys=%S maxrss_kb=%M" \
  julia --threads=auto --startup-file=no --history-file=no Main.jl
CMD
        ;;
    lean)
        cat <<'CMD'
export PATH=/workdir/.elan/bin:$PATH
cp /repo/dockerfiles/tests/lean/Main.lean /workdir/atcoder/Main.lean
cd /workdir/atcoder
/usr/bin/time -f "[time][lean][compile] real=%e user=%U sys=%S maxrss_kb=%M" lake -q build
/usr/bin/time -f "[time][lean][execute] real=%e user=%U sys=%S maxrss_kb=%M" ./.lake/build/bin/atcoder
CMD
        ;;
    ocaml)
        cat <<'CMD'
cp /repo/dockerfiles/tests/ocaml/main.ml /workdir/main.ml
eval "$(opam env --switch=5.3.0+flambda)"
/usr/bin/time -f "[time][ocaml][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  ocamlfind ocamlopt -O2 -o /workdir/a.out \
  /workdir/main.ml -linkpkg -thread \
  -package str,num,zarith,threads,containers,core,iter,batteries
/usr/bin/time -f "[time][ocaml][execute] real=%e user=%U sys=%S maxrss_kb=%M" /workdir/a.out
CMD
        ;;
    perl)
        cat <<'CMD'
cp /repo/dockerfiles/tests/perl/Main.pl /workdir/Main.pl
/usr/bin/time -f "[time][perl][compile] real=%e user=%U sys=%S maxrss_kb=%M" perl -c /workdir/Main.pl
/usr/bin/time -f "[time][perl][execute] real=%e user=%U sys=%S maxrss_kb=%M" perl /workdir/Main.pl
CMD
        ;;
    pypy)
        cat <<'CMD'
cp /repo/dockerfiles/tests/pypy/Main.py /workdir/Main.py
/usr/bin/time -f "[time][pypy][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  pypy3 -m py_compile /workdir/Main.py
/usr/bin/time -f "[time][pypy][execute-online-judge] real=%e user=%U sys=%S maxrss_kb=%M" \
  bash -lc 'pypy3 /workdir/Main.py ONLINE_JUDGE 2>/dev/null || true'
/usr/bin/time -f "[time][pypy][execute] real=%e user=%U sys=%S maxrss_kb=%M" \
  pypy3 -X int_max_str_digits=0 /workdir/Main.py
CMD
        ;;
    python)
        cat <<'CMD'
cp /repo/dockerfiles/tests/python/Main.py /workdir/Main.py
/usr/bin/time -f "[time][python][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  python3.13 -m py_compile /workdir/Main.py
/usr/bin/time -f "[time][python][execute-online-judge] real=%e user=%U sys=%S maxrss_kb=%M" \
  bash -lc 'python3.13 /workdir/Main.py ONLINE_JUDGE 2>/dev/null || true'
/usr/bin/time -f "[time][python][execute] real=%e user=%U sys=%S maxrss_kb=%M" \
  python3.13 -X int_max_str_digits=0 /workdir/Main.py
CMD
        ;;
    rust)
        cat <<'CMD'
cp /repo/dockerfiles/tests/rust/main.rs /workdir/src/main.rs
cd /workdir
/usr/bin/time -f "[time][rust][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  env CARGO_NET_OFFLINE=true cargo build --release --quiet --offline
/usr/bin/time -f "[time][rust][execute] real=%e user=%U sys=%S maxrss_kb=%M" ./target/release/main
CMD
        ;;
    typescript)
        cat <<'CMD'
cp /repo/dockerfiles/tests/typescript/Main.ts /workdir/Main.ts
/usr/bin/time -f "[time][typescript][compile] real=%e user=%U sys=%S maxrss_kb=%M" \
  bash -lc 'tsc /workdir/Main.ts --target ESNext --moduleResolution nodenext --module NodeNext --noEmitOnError --pretty true | ansifilter 1>&2'
/usr/bin/time -f "[time][typescript][execute] real=%e user=%U sys=%S maxrss_kb=%M" \
  /workdir/node.sh 1048576 /workdir/Main.js ONLINE_JUDGE ATCODER
CMD
        ;;
    *)
        return 1
        ;;
    esac
}

run_one() {
    local lang="$1"
    local cmd
    local image=""
    cmd="$(command_for_lang "${lang}")"

    if [[ -n "${IMAGE_PREFIX}" ]]; then
        image="${IMAGE_PREFIX}:${lang}-${TAG}"
        if ! docker image inspect "${image}" >/dev/null 2>&1; then
            echo "[${lang}] image not found: ${image}" >&2
            return 1
        fi
    else
        local candidate
        for candidate in "ale-bench:${lang}-${TAG}" "yimjk/ale-bench:${lang}-${TAG}"; do
            if docker image inspect "${candidate}" >/dev/null 2>&1; then
                image="${candidate}"
                break
            fi
        done
        if [[ -z "${image}" ]]; then
            echo "[${lang}] image not found (tried: ale-bench:${lang}-${TAG}, yimjk/ale-bench:${lang}-${TAG})" >&2
            return 1
        fi
    fi

    echo "[${lang}] image=${image}"
    local start_time stderr_file
    start_time="$(date +%s.%N)"
    stderr_file="$(mktemp)"
    docker run --rm \
        --cpus=1 \
        --memory=2g \
        --network=none \
        --user "${USER_ID}:${GROUP_ID}" \
        -e HOME=/workdir \
        -e XDG_CACHE_HOME=/workdir/.cache \
        -e XDG_CONFIG_HOME=/workdir/.config \
        -e XDG_DATA_HOME=/workdir/.local/share \
        -e HEAVY_SECONDS="${HEAVY_SECONDS}" \
        -v "${REPO_ROOT}:/repo:ro" \
        -w /workdir \
        "${image}" \
        bash -lc "set -Eeuo pipefail; mkdir -p \"\${HOME}\" \"\${XDG_CACHE_HOME}\" \"\${XDG_CONFIG_HOME}\" \"\${XDG_DATA_HOME}\"; ${cmd}" 2>"${stderr_file}"
    local exit_code=$?
    local end_time
    end_time="$(date +%s.%N)"
    elapsed="$(printf '%.1f' "$(echo "${end_time} - ${start_time}" | bc)")"
    echo "[${lang}] elapsed: ${elapsed}s"
    if [[ "${exit_code}" -ne 0 ]]; then
        cat "${stderr_file}" >&2
    elif [[ "${QUIET}" -ne 1 ]]; then
        cat "${stderr_file}" >&2
    fi
    rm -f "${stderr_file}"
    return "${exit_code}"
}

failed=0
for lang in "${LANGS[@]}"; do
    echo "========================================"
    if run_one "${lang}"; then
        echo "[${lang}] PASS"
    else
        echo "[${lang}] FAIL" >&2
        failed=1
    fi
done

if [[ "${failed}" -ne 0 ]]; then
    echo "Some language tests failed." >&2
    exit 1
fi

echo "All language tests passed."
