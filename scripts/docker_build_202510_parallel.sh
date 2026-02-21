#!/bin/bash
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage:
  scripts/docker_build_202510_parallel.sh [options]

Options:
  --mode <base|final|both>  Build target set (default: both)
  -j, --jobs <N>            Parallel build jobs (default: 4)
  --uid <UID>               UID build arg for final images (default: 0)
  --gid <GID>               GID build arg for final images (default: 0)
  --log-dir <PATH>          Log directory root (default: <repo>/logs/docker-build-202510)
  -h, --help                Show this help

Examples:
  scripts/docker_build_202510_parallel.sh --mode base -j 6
  scripts/docker_build_202510_parallel.sh --mode final --uid 1000 --gid 1000
EOF
}

is_uint() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_CONTEXT="${REPO_ROOT}/dockerfiles"

MODE="both"
JOBS=4
USER_ID=0
GROUP_ID=0
LOG_ROOT="${REPO_ROOT}/logs/docker-build-202510"

while [[ $# -gt 0 ]]; do
    case "$1" in
    --mode)
        MODE="${2:-}"
        shift 2
        ;;
    -j | --jobs)
        JOBS="${2:-}"
        shift 2
        ;;
    --uid)
        USER_ID="${2:-}"
        shift 2
        ;;
    --gid)
        GROUP_ID="${2:-}"
        shift 2
        ;;
    --log-dir)
        LOG_ROOT="${2:-}"
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

if [[ "${MODE}" != "base" && "${MODE}" != "final" && "${MODE}" != "both" ]]; then
    echo "Invalid --mode: ${MODE}" >&2
    exit 1
fi
if ! is_uint "${JOBS}" || [[ "${JOBS}" -lt 1 ]]; then
    echo "--jobs must be a positive integer: ${JOBS}" >&2
    exit 1
fi
if ! is_uint "${USER_ID}" || ! is_uint "${GROUP_ID}" ; then
    echo "--uid/--gid must be non-negative integers: uid=${USER_ID}, gid=${GROUP_ID}" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "docker command not found." >&2
    exit 1
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${LOG_ROOT}/${TIMESTAMP}"
mkdir -p "${LOG_DIR}"

readonly IMAGES=(
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
    all
    all-lean
)

PIDS=()
NAMES=()
OUT_LOGS=()
ERR_LOGS=()

reset_jobs() {
    PIDS=()
    NAMES=()
    OUT_LOGS=()
    ERR_LOGS=()
}

running_jobs_count() {
    jobs -pr | wc -l | tr -d ' '
}

wait_for_slot() {
    while [[ "$(running_jobs_count)" -ge "${JOBS}" ]]; do
        sleep 0.5
    done
}

launch_job() {
    local name="$1"
    shift
    local out_log="${LOG_DIR}/${name}.stdout.log"
    local err_log="${LOG_DIR}/${name}.stderr.log"

    (
        printf '[%s] START %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "${name}"
        "$@"
        rc=$?
        printf '[%s] END %s (exit=%s)\n' "$(date +'%Y-%m-%d %H:%M:%S')" "${name}" "${rc}"
        exit "${rc}"
    ) >"${out_log}" 2>"${err_log}" &

    PIDS+=("$!")
    NAMES+=("${name}")
    OUT_LOGS+=("${out_log}")
    ERR_LOGS+=("${err_log}")
}

run_base_stage() {
    local image
    reset_jobs
    echo "[base] launching ${#IMAGES[@]} builds (jobs=${JOBS})"

    for image in "${IMAGES[@]}"; do
        wait_for_slot
        launch_job \
            "base_${image//-/_}-202510" \
            docker build -q "${DOCKER_CONTEXT}" \
            -t "yimjk/ale-bench:${image}-202510" \
            -f "${DOCKER_CONTEXT}/Dockerfile_${image//-/_}_202510_base"
    done
}

run_final_stage() {
    local image
    reset_jobs
    echo "[final] launching ${#IMAGES[@]} builds (jobs=${JOBS}, uid=${USER_ID}, gid=${GROUP_ID})"

    for image in "${IMAGES[@]}"; do
        wait_for_slot
        launch_job \
            "final_${image//-/_}-202510" \
            docker build -q "${DOCKER_CONTEXT}" \
            -t "ale-bench:${image}-202510" \
            -f "${DOCKER_CONTEXT}/Dockerfile_${image//-/_}_202510" \
            --build-arg "UID=${USER_ID}" \
            --build-arg "GID=${GROUP_ID}"
    done
}

wait_stage() {
    local stage="$1"
    local failed=0
    local i
    local status

    echo "[${stage}] waiting for completion..."
    for i in "${!PIDS[@]}"; do
        if wait "${PIDS[$i]}"; then
            status="OK"
        else
            status="FAILED"
            failed=1
        fi
        echo "[${stage}] ${status} ${NAMES[$i]}"
        echo "  stdout: ${OUT_LOGS[$i]}"
        echo "  stderr: ${ERR_LOGS[$i]}"
    done

    return "${failed}"
}

echo "Log directory: ${LOG_DIR}"
overall_failed=0

if [[ "${MODE}" == "base" || "${MODE}" == "both" ]]; then
    run_base_stage
    if ! wait_stage "base"; then
        overall_failed=1
    fi
fi

if [[ "${MODE}" == "final" ]]; then
    run_final_stage
    if ! wait_stage "final"; then
        overall_failed=1
    fi
elif [[ "${MODE}" == "both" ]]; then
    if [[ "${overall_failed}" -ne 0 ]]; then
        echo "[final] skipped because base stage failed." >&2
    else
        run_final_stage
        if ! wait_stage "final"; then
            overall_failed=1
        fi
    fi
fi

if [[ "${overall_failed}" -ne 0 ]]; then
    echo "Some builds failed. Check logs under: ${LOG_DIR}" >&2
    exit 1
fi

echo "All requested builds succeeded. Logs: ${LOG_DIR}"
