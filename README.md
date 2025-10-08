# ALE-Bench

[![GitHub license](https://img.shields.io/github/license/SakanaAI/ALE-Bench?logo=github)](https://github.com/SakanaAI/ALE-Bench/blob/main/LICENSE)
[![GitHub check](https://github.com/SakanaAI/ALE-Bench/actions/workflows/check.yml/badge.svg)](https://github.com/SakanaAI/ALE-Bench/actions/workflows/check.yml)
[![GitHub stars](https://img.shields.io/github/stars/SakanaAI/ALE-Bench?logo=github)](https://github.com/SakanaAI/ALE-Bench/stargazers)
[![GitHub downloads](https://img.shields.io/github/downloads/SakanaAI/ALE-Bench/total?logo=github)](https://github.com/SakanaAI/ALE-Bench/releases)
[![Hugging Face repository](https://img.shields.io/badge/Hugging%20Face-SakanaAI%2FALE--Bench-FFD21E?logo=huggingface)](https://huggingface.co/datasets/SakanaAI/ALE-Bench)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-yimjk%2Fale--bench-1D63ED?logo=docker)](https://hub.docker.com/r/yimjk/ale-bench)
[![arXiv](https://img.shields.io/badge/arXiv-2506.09050-B31B1B?logo=data:image/svg+xml;base64,PHN2ZyBpZD0ibG9nb21hcmsiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgdmlld0JveD0iMCAwIDE3LjczMiAyNC4yNjkiPjxnIGlkPSJ0aW55Ij48cGF0aCBkPSJNNTczLjU0OSwyODAuOTE2bDIuMjY2LDIuNzM4LDYuNjc0LTcuODRjLjM1My0uNDcuNTItLjcxNy4zNTMtMS4xMTdhMS4yMTgsMS4yMTgsMCwwLDAtMS4wNjEtLjc0OGgwYS45NTMuOTUzLDAsMCwwLS43MTIuMjYyWiIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTU2Ni45ODQgLTI3MS41NDgpIiBmaWxsPSIjYmRiOWI0Ii8+PHBhdGggZD0iTTU3OS41MjUsMjgyLjIyNWwtMTAuNjA2LTEwLjE3NGExLjQxMywxLjQxMywwLDAsMC0uODM0LS41LDEuMDksMS4wOSwwLDAsMC0xLjAyNy42NmMtLjE2Ny40LS4wNDcuNjgxLjMxOSwxLjIwNmw4LjQ0LDEwLjI0MmgwbC02LjI4Miw3LjcxNmExLjMzNiwxLjMzNiwwLDAsMC0uMzIzLDEuMywxLjExNCwxLjExNCwwLDAsMCwxLjA0LjY5QS45OTIuOTkyLDAsMCwwLDU3MSwyOTNsOC41MTktNy45MkExLjkyNCwxLjkyNCwwLDAsMCw1NzkuNTI1LDI4Mi4yMjVaIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtNTY2Ljk4NCAtMjcxLjU0OCkiIGZpbGw9IiNiMzFiMWIiLz48cGF0aCBkPSJNNTg0LjMyLDI5My45MTJsLTguNTI1LTEwLjI3NSwwLDBMNTczLjUzLDI4MC45bC0xLjM4OSwxLjI1NGEyLjA2MywyLjA2MywwLDAsMCwwLDIuOTY1bDEwLjgxMiwxMC40MTlhLjkyNS45MjUsMCwwLDAsLjc0Mi4yODIsMS4wMzksMS4wMzksMCwwLDAsLjk1My0uNjY3QTEuMjYxLDEuMjYxLDAsMCwwLDU4NC4zMiwyOTMuOTEyWiIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTU2Ni45ODQgLTI3MS41NDgpIiBmaWxsPSIjYmRiOWI0Ii8+PC9nPjwvc3ZnPg==)](https://arxiv.org/abs/2506.09050)
[![Sakana AI Blog English](https://img.shields.io/badge/Sakana%20AI-Blog%20(English)-E10600?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAFXElEQVRoge2XW4yV1RXHf+s751v7zDlnwAnMKNgRCOUmBi/BYipNG2MTrKaRanyxqdUH+sCTb5poYrz0og8afWjqQ9OkCbZAkza0pU0sA0RroiZ4GQtmZphvf+coUGC4zIU5l+9bfZghJQPMnDnDmCY9v8dvr732+q9v77XXhhYtWrRo0aJFi/9fZD6dG2SPQqFYIJckuBpkAyMwsERIMgHV0QyV3DCjy6EiYLNd45oLMMgcVW7OBtwRpKxLYSWwFOhEKABqkIoxanAW4YSkRAR8jtCbZuhdPsqJRsVcMwG9oAuU+0zYjrEO6ADyF9cQOGcwBIwahCIsFKPTIDPpoopwHuOMwadBwJ7ucXYIVOdNgIHEcF3i2JwxngXuNKgJnBLwQE8iHKTCR8u5PKvHoTCaZ10m4S4x7gXWAx0CCw2yCE8uq/DavAj4EMJOxxYznhDYAgQI7xrsDVL2S43ebrjQqD8DKeVZYnW+CfwUWCWw9aYqf2w2xqtSdqyOHLu8ctorqVfMK/88WuB6g2AuvmPHSq986ZULR6B9JvuGFzMIjha4PgrZnsB+MR5GqItwEBgGlgVVbhRI5yKAiW20BOHA2gm/09KQgCPQXsrxo0ydXSK8gZEX2IHwqDh+gPAJsEgCNtvcz9UDAAJ7GrHPzmRQCvmGwcuWcgfQjvAZ8FRbhQOdMMw4lBx/SuFuMW49Bm3AWDPB94ET2GowXDMOzlnAgGNVauwEugXKwCtJhVdWwPildkmGt6UOqbByrEiRkeYEOGWrGYsRevIhx6cvoA0IcMpQWmW3pWRS+O37NT5+BJKpdjbGYZSaGF1tCa6Z4I9AuwnbMOoYB24Y4Uwj86YV8LVhTpfg2QRsatYvZQWMR8KQQKFmM2/LK9Hm+A7GbcDJxNgrUG9k3oyHuBsuXBq8QWYQciVoM9DnJn00uuCVGICFGD8EOgz+saLGB43ObShb/UW6tMbtkrImEm4MhAUpZD2MP26c/nFATMoCgy/CYPZCQuV7BvchHEvg+dk0ddOWvMEcyzPGdjMeZKK3aQd0ipkxcePmBYZSeHVkIa/dcpKRRgLod3w9hHcwFoux7aYav240+GkFlJVH6sIbYnQBI8ApjH6EQwhlJtrfvMEaM7YILJsUIwhejKdzVfZ0cXUhcZ6lVmc3sCmAPxSrbOuAs7MRcNUtlAj3yMSB/D3wZwt4d9k4fupNaxBEyg5gqQh7MRzGvQZvjik7jwW8sGSc6LIEwaKkzs+AjcCRNMsvOqqzC35avoTFJceqPlgwnZ1XbvZK5B3H4xzfKsMiH/KYdxzzShIp7w0qa6eIznlll1cqXjlTDrlrrjd4UxhkY+WZSKnGjr8bhJPfpZTj25FyeLLR+0uUZ4lBUHas9o59Xkm9o1TOcc9XHvhFSsqGSPncK6MDOTZPHR8I2eiVQ7FSjx2/LCmPxsqHk3/msHc80NNgJbzmlKDNOw56JY2VF6/WRpdCNsWO2CuVSDnnFYsdPQOO1Tv/+xprmmbUS3+RzqTKrwLjbhP2acjrUr38cJ8osrha4XabKL0qwlkx3hyr8HwjrfK84JX1XtkdKdVI+bjUxqapB/DfUBzM8Vjs2D/54DkXKW95x3d7L79HvhoMst7xk0iJYqUeKR994VgzNfg4ZKMP2Rcp571i3vGv2PH9marZvDOorPVKX6Scj5S3+ot0XRwzCKIcK3yOn3tl1CtJrMSDynOliffBvNFw7e0DFyoPGVha4K8rz3Du4ljkuD8wXjLYAAyZ8Lsg5TfdNQ7JFdrv/zki5QWv1L3jb3HInfOd9WtOD2TLBW7to7nHTIsWLVq0aNEs/wHPLhDZrKccngAAAABJRU5ErkJggg==)](https://sakana.ai/ale-bench/)
[![Sakana AI Blog Japanese](https://img.shields.io/badge/Sakana%20AI-Blog%20(Japanese)-E10600?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAFXElEQVRoge2XW4yV1RXHf+s751v7zDlnwAnMKNgRCOUmBi/BYipNG2MTrKaRanyxqdUH+sCTb5poYrz0og8afWjqQ9OkCbZAkza0pU0sA0RroiZ4GQtmZphvf+coUGC4zIU5l+9bfZghJQPMnDnDmCY9v8dvr732+q9v77XXhhYtWrRo0aJFi/9fZD6dG2SPQqFYIJckuBpkAyMwsERIMgHV0QyV3DCjy6EiYLNd45oLMMgcVW7OBtwRpKxLYSWwFOhEKABqkIoxanAW4YSkRAR8jtCbZuhdPsqJRsVcMwG9oAuU+0zYjrEO6ADyF9cQOGcwBIwahCIsFKPTIDPpoopwHuOMwadBwJ7ucXYIVOdNgIHEcF3i2JwxngXuNKgJnBLwQE8iHKTCR8u5PKvHoTCaZ10m4S4x7gXWAx0CCw2yCE8uq/DavAj4EMJOxxYznhDYAgQI7xrsDVL2S43ebrjQqD8DKeVZYnW+CfwUWCWw9aYqf2w2xqtSdqyOHLu8ctorqVfMK/88WuB6g2AuvmPHSq986ZULR6B9JvuGFzMIjha4PgrZnsB+MR5GqItwEBgGlgVVbhRI5yKAiW20BOHA2gm/09KQgCPQXsrxo0ydXSK8gZEX2IHwqDh+gPAJsEgCNtvcz9UDAAJ7GrHPzmRQCvmGwcuWcgfQjvAZ8FRbhQOdMMw4lBx/SuFuMW49Bm3AWDPB94ET2GowXDMOzlnAgGNVauwEugXKwCtJhVdWwPildkmGt6UOqbByrEiRkeYEOGWrGYsRevIhx6cvoA0IcMpQWmW3pWRS+O37NT5+BJKpdjbGYZSaGF1tCa6Z4I9AuwnbMOoYB24Y4Uwj86YV8LVhTpfg2QRsatYvZQWMR8KQQKFmM2/LK9Hm+A7GbcDJxNgrUG9k3oyHuBsuXBq8QWYQciVoM9DnJn00uuCVGICFGD8EOgz+saLGB43ObShb/UW6tMbtkrImEm4MhAUpZD2MP26c/nFATMoCgy/CYPZCQuV7BvchHEvg+dk0ddOWvMEcyzPGdjMeZKK3aQd0ipkxcePmBYZSeHVkIa/dcpKRRgLod3w9hHcwFoux7aYav240+GkFlJVH6sIbYnQBI8ApjH6EQwhlJtrfvMEaM7YILJsUIwhejKdzVfZ0cXUhcZ6lVmc3sCmAPxSrbOuAs7MRcNUtlAj3yMSB/D3wZwt4d9k4fupNaxBEyg5gqQh7MRzGvQZvjik7jwW8sGSc6LIEwaKkzs+AjcCRNMsvOqqzC35avoTFJceqPlgwnZ1XbvZK5B3H4xzfKsMiH/KYdxzzShIp7w0qa6eIznlll1cqXjlTDrlrrjd4UxhkY+WZSKnGjr8bhJPfpZTj25FyeLLR+0uUZ4lBUHas9o59Xkm9o1TOcc9XHvhFSsqGSPncK6MDOTZPHR8I2eiVQ7FSjx2/LCmPxsqHk3/msHc80NNgJbzmlKDNOw56JY2VF6/WRpdCNsWO2CuVSDnnFYsdPQOO1Tv/+xprmmbUS3+RzqTKrwLjbhP2acjrUr38cJ8osrha4XabKL0qwlkx3hyr8HwjrfK84JX1XtkdKdVI+bjUxqapB/DfUBzM8Vjs2D/54DkXKW95x3d7L79HvhoMst7xk0iJYqUeKR994VgzNfg4ZKMP2Rcp571i3vGv2PH9marZvDOorPVKX6Scj5S3+ot0XRwzCKIcK3yOn3tl1CtJrMSDynOliffBvNFw7e0DFyoPGVha4K8rz3Du4ljkuD8wXjLYAAyZ8Lsg5TfdNQ7JFdrv/zki5QWv1L3jb3HInfOd9WtOD2TLBW7to7nHTIsWLVq0aNEs/wHPLhDZrKccngAAAABJRU5ErkJggg==)](https://sakana.ai/ale-bench-jp/)
[![ALE-Bench Leaderboard](https://img.shields.io/badge/ALE--Bench-Leaderboard-FFD700?logo=github&logoColor=white)](https://sakanaai.github.io/ALE-Bench-Leaderboard/)

**ALE-Bench** is a benchmark for evaluating AI systems on score-based algorithmic programming contests.
Drawing on real-world tasks from the AtCoder Heuristic Contest (AHC), ALE-Bench presents optimization problems (e.g., routing and scheduling) that are computationally hard and admit no known exact solution.

*Note: This repository is not an official product of SakanaAI or AtCoder and is therefore not officially supported.*

***Important: Please do not use this repository to participate in AHCs ([AtCoder Heuristic Contest Generative AI Usage Rules - Version 20250616](https://info.atcoder.jp/entry/ahc-llm-rules-en)).***

https://github.com/user-attachments/assets/50a8de5a-b519-4aef-8e54-c60ac9dcbb90

## Table of Contents
- [Setup](#setup)
- [Evaluation](#evaluation)
- [Documentation](#documentation)
- [Development and Contributing](#development-and-contributing)
- [Citation](#citation)

## Setup

1.  **Install Docker:**
    Follow the official instructions at [docker.com](https://docs.docker.com/engine/install/).

2.  **Install CairoSVG Dependencies:**
    Refer to the [CairoSVG documentation](https://cairosvg.org/documentation/#how-to-use-cairosvg).
    ```sh
    # Linux
    sudo apt install libcairo2-dev libffi-dev
    # macOS
    brew install cairo libffi pkgconf
    export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
    export DYLD_LIBRARY_PATH="/usr/local/lib:/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
    ```
    *Note: These paths might vary depending on your macOS version and Homebrew installation. If you encounter issues, verify the correct paths for `cairo` and `libffi` installed by Homebrew.*

3.  **Install Python (3.9 - 3.14) and ALE-Bench Toolkit:**
    ```sh
    # Install via this GitHub repository
    pip install git+https://github.com/SakanaAI/ALE-Bench.git

    # Or clone this GitHub repository and install locally
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    pip install .
    pip install ".[eval]"  # For evaluation dependencies

    # Using uv (recommended for faster environment management)
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    uv venv --python 3.12.11  # Or any supported Python version (3.9 ~ 3.14)
    uv sync
    uv sync --extra eval  # For evaluation dependencies
    source .venv/bin/activate
    ```

    > **Note**: We require Python 3.10 or higher when using the `eval` extra (for evaluation dependencies) due to dependencies on Pydantic AI.

4.  **Build Docker Images:**
    This script will build the necessary Docker execution images for ALE-Bench. It automatically pulls pre-built base images from Docker Hub (repository: `yimjk/ale-bench`) and then creates local images tagged as `ale-bench:<language>-<version>` with appropriate permissions for your user.
    ```sh
    bash ./scripts/docker_build_all.sh $(id -u) $(id -g)
    # Or you can build images for specific version (202301)
    bash ./scripts/docker_build_202301.sh $(id -u) $(id -g)
    ```
    If you prefer to pull all base images beforehand, you can optionally run:
    ```sh
    bash ./scripts/docker_pull_all.sh
    # Or pull images for specific version (202301)
    bash ./scripts/docker_pull_202301.sh
    ```

5.  **[Optional] Download Data via Hugging Face Repository:**
    ```sh
    # Create a directory for the data
    mkdir -p /tmp/data && cd /tmp/data
    git lfs install
    git clone https://huggingface.co/datasets/SakanaAI/ALE-Bench
    # Set the ALE_BENCH_DATA environment variable to use this local copy.
    # If not set, data will be downloaded on demand using hf_hub_download (default).
    export ALE_BENCH_DATA=/tmp/data/ALE-Bench
    ```

## Evaluation

For fair and reproducible performance comparisons, we **strongly recommend** running evaluations on a consistent, specified AWS instance (e.g., `c6i.32xlarge`).

We provide a Terraform configuration to set up the necessary environment, including the ALE-Bench toolkit and required dependencies.
Please refer to the [AWS Evaluation Guide](./docs/aws_evaluation.md) for detailed instructions on setting up and running evaluations in AWS.

We also provide a comprehensive framework for evaluating Large Language Models (LLMs) for ALE-Bench (scripts: [ale_bench_eval](./src/ale_bench_eval/)). Please read the [ALE-Bench Evaluation Tool documentation](./docs/evaluation.md) for more details.

There is a MCP (Model Context Protocol) server feature to simplify the use of ALE-Bench as a tool. For setup and usage instructions, please refer to the [MCP Server documentation](./docs/mcp_server.md).

### Example Evaluation Script

Below is an example script demonstrating how to use the ALE-Bench toolkit for evaluating an AI agent on a specific problem (e.g., `ahc001`).

```python
import ale_bench
import ale_bench.utils
import datetime as dt

# Start a new evaluation session
session = ale_bench.start(
    problem_id="ahc001",
    lite_version=False,
    num_workers=13,  # Adjust based on your machine's physical cores
    run_visualization_server=True,
    visualization_server_port=8080
)

# NOTE: While the `session` object contains attributes like `private_seeds`,
# `rank_performance_map`, and `standings`, these (and any other attributes
# prefixed with an underscore, e.g., `_private_inputs`) MUST NOT be accessed
# or used during your experiment to ensure fair evaluation.

# Access problem details
problem = session.problem
problem_statement_md = problem.statement  # Markdown-formatted problem statement
problem_images = problem.statement_images  # Associated images
problem_constraints_obj = problem.constraints  # Structured constraints

# --- Your Agent's Logic Begins ---

# Example: Constructing an initial prompt for an LLM/LMM
# (Replace with your agent's prompt engineering)
initial_messages = my_agent.construct_initial_prompt(
    problem_statement_md,
    problem_images,
    problem_constraints_obj
)

# Utility for parsing problem statements (e.g., for OpenAI models)
parsed_content = ale_bench.utils.parse_statement(
    problem_statement_md, problem_images, return_openai=True
)

# Obtain a solution from your LLM/LMM agent
agent_response = my_agent.get_llm_response(initial_messages)
extracted_code = my_agent.parse_code_from_response(agent_response)
detected_language = my_agent.detect_code_language(extracted_code)
# Ensure detected_language is one of: "cpp17", "cpp20", "cpp23", "python", "rust"

# Evaluate against public test cases
public_result = session.public_eval(extracted_code, code_language=detected_language)
print(f"Initial Public Score: {public_result.overall_absolute_score}")

# Iterative refinement loop (example)
solution_attempts = [(extracted_code, public_result)]
current_best_code = extracted_code

# Define your maximum refinement iterations, e.g., MAX_REFINEMENT_ITERATIONS = 5
for i in range(MAX_REFINEMENT_ITERATIONS):
    feedback_prompt = my_agent.construct_feedback_prompt(
        problem, current_best_code, public_result
    )
    refined_response = my_agent.get_llm_response(feedback_prompt)
    refined_code = my_agent.parse_code_from_response(refined_response)

    if refined_code: # Agent might not always produce new code
        public_result = session.public_eval(refined_code, code_language=detected_language)
        solution_attempts.append((refined_code, public_result))
        # Update current_best_code based on problem's score type (minimize/maximize)
        # (Implementation depends on your agent's strategy)
        current_best_code = my_agent.select_best_code(solution_attempts, problem.metadata.score_type)
    else:
        print(f"Iteration {i+1}: No new code generated.")
        break # Or implement other logic like re-prompting

# Select the final submission based on overall public performance
final_submission_code = my_agent.select_best_code(solution_attempts, problem.metadata.score_type)

# --- Your Agent's Logic Ends ---

# Evaluate the final submission against private test cases
# Ensure `lite_version=False` during session start for rank and performance calculation.
private_result, final_rank, final_performance = session.private_eval(
    final_submission_code, code_language=detected_language
)
print(f"Final Private Score: {private_result.overall_absolute_score}")
print(f"Rank: {final_rank}, Performance: {final_performance}")

# Monitor resource consumption
print(f"Current Resource Usage: {session.current_resource_usage}")
print(f"Remaining Resources: {session.remaining_resource_usage}")

# Inspect local Rust tool sources (if applicable)
if session.problem.metadata.problem_type == "reactive": # Example condition
    ale_bench.utils.print_dir_tree(session.rust_src_dir)

# Persist session state for later analysis or resumption
session.save("my_ahc001_session.json")

# Explicitly close the session to release resources
session.close()

# To resume a saved session:
# resumed_session = ale_bench.restart("/path/to/my_ahc001_session.json")

# To clear all cached ALE-Bench data (problem data, toolchains):
# ale_bench.clear_cache()
```

## Documentation
For more details about ALE-Bench, please refer to the [docs/](./docs/) directory.

## Development and Contributing
Please see the [CONTRIBUTING.md](./CONTRIBUTING.md) file.

## Citation

Please cite ALE-Bench as follows:

```bibtex
@inproceedings{imajuku2025alebench,
    title = {{ALE}-Bench: A Benchmark for Long-Horizon Objective-Driven Algorithm Engineering},
    author = {Yuki Imajuku and Kohki Horie and Yoichi Iwata and Kensho Aoki and Naohiro Takahashi and Takuya Akiba},
    booktitle = {The Thirty-ninth Annual Conference on Neural Information Processing Systems Datasets and Benchmarks Track},
    year = {2025},
    url = {https://openreview.net/forum?id=JCjGvbsOmQ}
}
```
