#!/bin/bash
set -Eeuo pipefail

config_name=${1:-}
root_path=${2:-}

if [ -z "${config_name}" ]; then
    echo "Usage: $0 <config_name> [root_path]"
    exit 1
fi

script_dir=$(cd $(dirname $0); pwd)
project_dir=$(cd ${script_dir}/..; pwd)
config_path=${project_dir}/llm_configs/${config_name}.json

if [ ! -f "${config_path}" ]; then
    echo "Error: Config file not found: ${config_path}"
    exit 1
fi

echo -e "Using config: ${config_path}"

dotenv_path=${project_dir}/.env
if [ -f "${dotenv_path}" ]; then
    echo -e "Loading environment variables from ${dotenv_path}"
    set -a
    source "${dotenv_path}"
    set +a
else
    echo -e "No .env file found at ${dotenv_path}, proceeding without loading environment variables."
fi

cd $project_dir
if [ -z "${root_path}" ]; then
    uv run -m ale_bench_eval --model_config_path $config_path \
        --n_repeated_sampling 15 --n_self_refine 16 --num_workers 10 --n_public_cases 50 \
        --code_language cpp20 --prompt_language en \
        --max_parallel_problems 5 --problem_ids_type all --selection_method median
else
    echo -e "Using root path: ${root_path}"
    uv run -m ale_bench_eval --model_config_path $config_path \
        --n_repeated_sampling 15 --n_self_refine 16 --num_workers 10 --n_public_cases 50 \
        --code_language cpp20 --prompt_language en \
        --max_parallel_problems 5 --problem_ids_type all --selection_method median \
        --root_path $root_path
fi
