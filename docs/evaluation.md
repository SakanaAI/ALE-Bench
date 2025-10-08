# ALE-Bench Evaluation Tool

A comprehensive framework for evaluating Large Language Models (LLMs) for ALE-Bench.

## Overview

The tool evaluates LLMs' performance on ALE-Bench problems using two evaluation strategies:

- **Repeated Sampling**: Generate multiple solutions and select one using configurable methods (best score or median)
- **Self-Refinement**: Iteratively improve the selected solution using feedback from evaluation results

## Installation

### Setup

1. Setup ALE-Bench as [ALE-Bench Setup Instructions](../README.md#setup):
```sh
uv venv --python 3.12.11  # Or any supported Python version (3.10 ~ 3.14)
uv sync --extra eval
```

> **Note**: We require Python 3.10 or higher due to dependencies on Pydantic AI.

> **Note**: The `eval` extra includes dependencies required for evaluation.

2. (Optional) Set up your LLM API credentials in [`.env`](../.env) (example in [.env.example](../.env.example)):
```sh
OPENAI_API_KEY="Your OpenAI API Key"
ANTHROPIC_API_KEY="Your Anthropic API Key"
GOOGLE_API_KEY="Your Google API Key"
OPENROUTER_API_KEY="Your OpenRouter API Key"
... # Add other environment variables as needed
```

> **Note**: `.env` is sourced by the script. Only include environment variable assignments you trust.

## Usage

### Basic Usage

1. Configure your model by creating a JSON file (e.g., [`gpt-5.json`](../llm_configs/gpt-5.json) in the [`llm_configs/`](../llm_configs/) directory). Example configuration:
```json
{
    "model_name": "gpt-5-2025-08-07",
    "provider": "openai",
    "settings": {
        "temperature": 1.0,
        "openai_reasoning_effort": "minimal"
    }
}
```

> **Note**: `model_name`, `provider`, and `settings` are necessary fields. Also, ensure that `timeout` field is not set in `settings` as it is internally managed.

> **Note**: See other example configurations in the [`llm_configs/`](../llm_configs/) directory.

2. Ensure setup is complete by running a quick test (change parameters as needed):
```bash
uv run -m ale_bench_eval --model_config_path llm_configs/gpt-5.json --num_workers 5 --n_public_cases 5 --max_parallel_problems 2 --problem_ids_type debug
```

3. (Optional) Modify parameters in the provided script [`scripts/run_eval.sh`](../scripts/run_eval.sh) as needed.

4. Run evaluation on all supported problems:

```bash
# Using the provided script
bash scripts/run_eval.sh gpt-5

# Or directly run using uv
uv run -m ale_bench_eval --model_config_path llm_configs/gpt-5.json --n_repeated_sampling 15 --n_self_refine 16 --num_workers 10 --n_public_cases 50 --code_language cpp20 --prompt_language en --max_parallel_problems 5 --problem_ids_type all --selection_method median
```

### Bash Script Arguments
The provided script [`scripts/run_eval.sh`](../scripts/run_eval.sh) accepts the following arguments:
```bash
bash scripts/run_eval.sh <config_name> [root_path]
```

- `<config_name>`: Name of the model configuration file (without `.json` extension) located in the `llm_configs/` directory (e.g., `gpt-5` for `llm_configs/gpt-5.json`)
- `[root_path]`: (Optional) Root path to save results and resume from (if not provided, a new directory will be created in `results/`)

### Command Line Arguments

| Parameter | Type | Default | Description |
|:---------:|:----:|:-------:|:------------|
| `model_config_path` | str | *required* | Path to the model inference configuration (provider/model/settings) file used by Pydantic AI |
| `n_repeated_sampling` | int | 1 | Number of repeated sampling iterations |
| `n_self_refine` | int | 1 | Number of self-refinement iterations including repeated sampling process (`1` means no self-refinement) |
| `num_workers` | int | 1 | Number of parallel case evaluation workers for each problem |
| `n_public_cases` | int | `None` | Number of cases to use for public evaluation (`None` means using ALE-Bench default: 50 for `all`, 5 for `lite`) |
| `code_language` | str | `cpp20` | Target programming language (`cpp17`, `cpp20`, `cpp23`, `python`, `rust`, `any`; `any` means LLM can select from `cpp20`, `python`, and `rust`) |
| `prompt_language` | str | `en` | Prompt language (`en` for English, `ja` for Japanese) |
| `max_parallel_problems` | int | `1` | Maximum number of problems to evaluate in parallel |
| `problem_ids_type` | str | `debug` | Problem ID set to evaluate (`debug`, `lite`, `all`) |
| `selection_method` | str | `median` | Method to select solution from repeated sampling (`best`, `median`) |
| `use_statement_image` | bool | `False` | Whether to use statement images in the evaluation process (requires a vision-capable model/provider) |
| `root_path` | str | `None` | Root path to save results and resume from (`None` means creating a new directory in `<current working directory>/results/`) |
| `skip_llm_inference` | bool | `False` | Skip LLM inference and only perform aggregation of existing results |

> **Note**: Ensure that `num_workers` $\times$ `max_parallel_problems` does not exceed the number of physical CPU cores available on your machine to avoid resource contention and performance degradation.

### Problem Selection

The framework supports three different problem sets:

- **`debug`** (default): Quick testing with 2 problems (`ahc027`, `ahc039`)
- **`lite`**: A curated subset of problems for faster comprehensive evaluation
- **`all`**: Complete set of all available ALE-Bench problems

Problem IDs are dynamically loaded from ALE-Bench using `list_problem_ids()`, ensuring compatibility with the latest problem sets.

## Output Structure

```
results/
└── <config_name>_YYYY-MM-DD_HH-MM-SS/
    ├── aggregated_results.json                             # Cross-problem statistics
    ├── experiment_settings.json                            # Experiment configuration
    ├── repeated_sampling.csv                               # Tabular results for repeated sampling
    ├── results.json                                        # Execution status summary
    ├── self_refine_<n>.csv                                 # Tabular results for self-refinement (n = number of iterations)
    ├── summary.txt                                         # Human-readable summary
    ├── time_taken.txt                                      # Overall execution time
    └── problem-id/
        ├── ale_bench_results/                              # ALE-Bench specific results
        │   ├── private_result_repeated_sampling.json       # Repeated sampling private result
        │   ├── private_result_self_refine_<n>.json         # Self-refinement private result (n = number of iterations)
        │   ├── repeated_sampling_results_<n>.json          # Repeated sampling public result (n = number of iterations)
        │   └── self_refine_results_<n>.json                # Self-refinement public result (n = number of iterations)
        ├── conversations/                                  # Conversations with LLM
        │   ├── repeated_sampling_conversations_<n>.json    # Repeated sampling conversations (n = number of iterations)
        │   └── self_refine_conversations.json              # Self-refinement conversations
        ├── results/
        │   ├── final_results.json                          # Private evaluation results
        │   ├── repeated_sampling_results.json              # Repeated sampling public evaluation results
        │   ├── self_refine_results.json                    # Self-refinement public evaluation results
        │   ├── time_taken.txt                              # Time taken for the problem
        │   └── total_cost.json                             # Estimated API cost
        └── logs.txt                                        # Execution logs
```

### Key Output Files

- **experiment_settings.json**: Records all parameters used for the experiment
- **aggregated_results.json**: Statistical summary across all problems including:
  - Mean/median ranks and performances for each method
  - Best performing method identification
  - Success/failure breakdown
- **final_results.json**: Private evaluation results for both repeated sampling and self-refinement strategies

## Architecture

### Evaluation Pipeline

1. **Parallel Initialization**: Launch multiple problem sessions in parallel
2. **Repeated Sampling**: Generate N candidate solutions per problem and evaluate each using the public score
3. **Solution Selection**: Select solution using specified method (`best` or `median`)
   - **best**: Select the solution with the highest/lowest score based on problem type
   - **median**: Select the solution closest to the median score
4. **Self-Refinement**: Iteratively refine the selected solution using feedback
5. **Private Evaluation**: Perform final evaluations on hidden test cases for both strategies
6. **Aggregation**: Compute statistical summaries across all problems

### Evaluation Code Structure

```
ALE-Bench/
├── docs/evaluation.md         # This documentation file
├── llm_configs/               # Model configuration files
├── results/                   # Output directory
├── scripts/run_eval.sh        # Evaluation runner script
├── src/ale_bench_eval/        # Core library
│   ├── codes/                 # Fallback COMPILATION_ERROR codes for each language
│   ├── prompts/               # Prompt management
│   │   ├── builder.py         # Prompt construction logic
│   │   └── texts.py           # Prompt templates
│   ├── __init__.py            # Package initializer
│   ├── __main__.py            # Entry point with CLI (main evaluation logic)
│   ├── analyze_results.py     # Result aggregation and analysis
│   ├── calc_cost.py           # Cost estimation logic
│   ├── data_types.py          # Pydantic models and type definitions
│   ├── evaluate.py            # Private evaluation logic
│   ├── logger.py              # Enhanced logging with isolation
│   ├── safe_ale_session.py    # Safe execution wrapper for ALE-Bench sessions
│   ├── safe_generation.py     # Safe LLM generation using Pydantic AI
│   ├── scaffolds.py           # Repeated sampling and self-refinement
│   └── selection.py           # Solution selection from repeated sampling
├── .env                       # Environment variables
├── .env.example               # Example environment file
├── .gitignore                 # Git ignore file
├── LICENSE                    # License file
├── README.md                  # ALE-Bench main README
├── pyproject.toml             # Project configuration
└── uv.lock                    # Dependency lock file
```
