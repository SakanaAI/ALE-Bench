#!/bin/bash
set -Eeuo pipefail

usage() {
    echo "Usage: $0 [options] <config_name>"
    echo "Options:"
    echo "  --root_path, -r <path>"
    echo "  --judge_version, -j <201907|202301|202510>"
    echo "  --code_language, -c <language>"
    echo "  --prompt_language, -p <en|ja>"
    echo "  --help, -h"
}

require_option_value() {
    local option_name=$1
    local option_value=${2:-}
    if [ -z "${option_value}" ] || [[ "${option_value}" == -* ]]; then
        echo "Error: Missing value for ${option_name}"
        usage
        exit 1
    fi
}

config_name=""
root_path=""
judge_version="202301"
code_language=""
prompt_language="en"

while [ $# -gt 0 ]; do
    case "$1" in
        --root_path|-r)
            require_option_value "$1" "${2:-}"
            root_path=${2:-}
            shift 2
            ;;
        --judge_version|-j)
            require_option_value "$1" "${2:-}"
            judge_version=${2:-}
            shift 2
            ;;
        --code_language|-c)
            require_option_value "$1" "${2:-}"
            code_language=${2:-}
            shift 2
            ;;
        --prompt_language|-p)
            require_option_value "$1" "${2:-}"
            prompt_language=${2:-}
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --*|-*)
            echo "Error: Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "${config_name}" ]; then
                config_name=$1
                shift
            else
                echo "Error: Unexpected argument: $1"
                usage
                exit 1
            fi
            ;;
    esac
done

if [ -z "${config_name}" ]; then
    echo "Error: Missing config_name."
    usage
    exit 1
fi

script_dir=$(cd "$(dirname "$0")" && pwd)
project_dir=$(cd "${script_dir}/.." && pwd)
config_path=${project_dir}/llm_configs/${config_name}.json

if [ ! -f "${config_path}" ]; then
    echo "Error: Config file not found: ${config_path}"
    exit 1
fi

echo -e "Using config: ${config_path}"

case "${judge_version}" in
    201907|202301|202510)
        ;;
    *)
        echo "Error: Invalid judge_version: ${judge_version}. Expected one of: 201907, 202301, 202510"
        exit 1
        ;;
esac

if [ -z "${code_language}" ]; then
    case "${judge_version}" in
        201907) code_language="cpp17" ;;
        202301) code_language="cpp20" ;;
        202510) code_language="cpp23" ;;
    esac
fi

case "${prompt_language}" in
    en|ja)
        ;;
    *)
        echo "Error: Invalid prompt_language: ${prompt_language}. Expected one of: en, ja"
        exit 1
        ;;
esac

echo -e "Using judge version: ${judge_version}"
echo -e "Using code language: ${code_language}"
echo -e "Using prompt language: ${prompt_language}"

dotenv_path=${project_dir}/.env
if [ -f "${dotenv_path}" ]; then
    echo -e "Loading environment variables from ${dotenv_path}"
    set -a
    source "${dotenv_path}"
    set +a
else
    echo -e "No .env file found at ${dotenv_path}, proceeding without loading environment variables."
fi

cd "$project_dir"

if [ -n "${root_path}" ]; then
    echo -e "Using root path: ${root_path}"
    uv run -m ale_bench_eval --model_config_path "$config_path" \
        --n_repeated_sampling 15 --n_self_refine 16 --num_workers 10 --n_public_cases 50 \
        --judge_version "$judge_version" --code_language "$code_language" --prompt_language "$prompt_language" \
        --max_parallel_problems 5 --problem_ids_type all --selection_method median \
        --root_path "$root_path"
else
    uv run -m ale_bench_eval --model_config_path "$config_path" \
        --n_repeated_sampling 15 --n_self_refine 16 --num_workers 10 --n_public_cases 50 \
        --judge_version "$judge_version" --code_language "$code_language" --prompt_language "$prompt_language" \
        --max_parallel_problems 5 --problem_ids_type all --selection_method median
fi
