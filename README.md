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

***Important: Please do not use this repository to participate　in AHCs ([AtCoder Heuristic Contest Generative AI Usage Rules - Version 20250616](https://info.atcoder.jp/entry/ahc-llm-rules-en)).***

https://github.com/user-attachments/assets/50a8de5a-b519-4aef-8e54-c60ac9dcbb90

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

3.  **Install Python (3.9 - 3.13) and ALE-Bench Toolkit:**
    ```sh
    # Install via this GitHub repository
    pip install git+https://github.com/SakanaAI/ALE-Bench.git

    # Or clone this GitHub repository and install locally
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    pip install .

    # Using uv (recommended for faster environment management)
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    uv venv --python 3.12.9  # Or any supported Python version (3.9 ~ 3.13)
    uv sync
    source .venv/bin/activate
    ```

4.  **Build Docker Images:**
    This script will build the necessary Docker execution images for ALE-Bench. It automatically pulls pre-built base images from Docker Hub (repository: `yimjk/ale-bench`) and then creates local images tagged as `ale-bench:<language>-<version>` with appropriate permissions for your user.
    ```sh
    bash ./scripts/docker_build_all.sh $(id -u) $(id -g)
    ```
    If you prefer to pull all base images beforehand, you can optionally run:
    ```sh
    bash ./scripts/docker_pull_all.sh
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

6.  **[Optional] Install AWS CLI and Terraform:**
    For cloud-based evaluations, install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [Terraform](https://developer.hashicorp.com/terraform/install).

## The `Session` Object

The `Session` object is central to ALE-Bench, encapsulating the state and functionalities for an evaluation session on a specific problem. It facilitates input case generation, code execution, visualization, and evaluation.

### Initialization

A session is initiated using the `ale_bench.start()` function:

```python
import ale_bench
import datetime as dt

session = ale_bench.start(
    problem_id="ahc001",              # Target problem ID
    lite_version=False,               # Use full dataset (True for a smaller subset)
    num_workers=13,                   # Parallel workers for judging (adjust based on CPU cores)
    run_visualization_server=True,    # Enable visualization server
    visualization_server_port=8080,   # Port for the visualization server (None to disable)
    session_duration=dt.timedelta(hours=2) # Optional: set a duration for the session
)
```

**Key Initialization Parameters for `ale_bench.start()`:**

- `problem_id (str)`: The ID of the problem to start a session for. This is a required parameter.
- `lite_version (bool, optional)`: If `True`, uses a smaller "lite" version of seeds and problem data for quicker evaluations. Defaults to `False`.
- `use_same_time_scale (bool, optional)`: If `True`, the session simulates contest time progression (e.g., limiting the frequency of `public_eval` calls as the submission interval in an actual contest). Defaults to `False`.
- `maximum_num_case_gen (int, optional)`: Maximum number of input cases that can be generated using `session.case_gen()` or `session.case_gen_eval()`. Defaults to a very large number (effectively unlimited).
- `maximum_num_case_eval (int, optional)`: Maximum number of input cases that can be evaluated using `session.case_eval()` or `session.case_gen_eval()`. Defaults to a very large number.
- `maximum_execution_time_case_eval (float, optional)`: Cumulative maximum execution time (in seconds) using `session.case_eval()` or `session.case_gen_eval()`. Defaults to a very large number.
- `maximum_num_call_public_eval (int, optional)`: Maximum number of times `session.public_eval()` can be called. Defaults to a very large number (but is overridden by problem-defined limits if `use_same_time_scale` is `True`).
- `session_duration (dt.timedelta | int | float, optional)`: Sets a maximum duration for the entire session. Can be a `datetime.timedelta` object, or seconds as an `int` or `float`. Defaults to `None` (uses the problem's predefined duration).
- `num_workers (int, optional)`: The number of worker processes to use for running judge evaluations in parallel. Defaults to `1`.
- `run_visualization_server (bool, optional)`: If `True`, attempts to start a local visualization server for the problem. Defaults to `False`.
- `visualization_server_port (int | None, optional)`: Specifies the port for the visualization server. If `None` and `run_visualization_server` is `True`, a free port between 9000-65535 will be automatically selected. Defaults to `None`.

### Core Methods

Each method is described below with its parameters and return values.

#### `case_gen`
Generates input case(s) based on the provided seed(s) and generation arguments.

**Parameters:**
- `seed (list[int] | int, optional)`: The seed or list of seeds for case generation. Defaults to `0`.
- `gen_kwargs (dict, optional)`: Dictionary of arguments for the case generator. Defaults to an empty dictionary.

**Returns:**
- `list[str] | str`: The generated case(s) as string(s). Returns a single string if `seed` is an `int`, or a list of strings if `seed` is a `list[int]`.

---
#### `case_eval`
Evaluates the provided code against the given input string(s). This method is intended for local evaluation, allowing users to specify custom time and memory limits.

**Parameters:**
- `input_str (list[str] | str)`: The input string or list of input strings for the evaluation.
- `code (str)`: The source code to be evaluated.
- `code_language (CodeLanguage | str)`: The programming language of the code. Can be a `CodeLanguage` enum member or its string representation (e.g., "python", "cpp17").
- `judge_version (JudgeVersion | str, optional)`: The version of the judge to use. Defaults to `None` (uses the latest or problem-specific default).
- `time_limit (float, optional)`: Custom time limit for execution in seconds. Defaults to `None` (uses problem-specific default).
- `memory_limit (int | str, optional)`: Custom memory limit for execution (e.g., `256_000_000` for 256MB, or "256m"). Defaults to `None` (uses problem-specific default).
- `skip_local_visualization (bool, optional)`: If `True`, skips generating local visualizations even if available. Defaults to `False`.

**Returns:**
- `Result`: A `Result` object containing the evaluation details, including scores, execution time, and memory usage for each case.

---
#### `case_gen_eval`
A convenience method that first generates test case(s) using specified seeds and generation arguments, and then immediately evaluates the provided code against these newly generated cases.

**Parameters:**
- `code (str)`: The source code to be evaluated.
- `code_language (CodeLanguage | str)`: The programming language of the code.
- `judge_version (JudgeVersion | str, optional)`: The judge version. Defaults to `None`.
- `seed (list[int] | int, optional)`: Seed(s) for case generation. Defaults to `0`.
- `time_limit (float, optional)`: Custom time limit in seconds. Defaults to `None`.
- `memory_limit (int | str, optional)`: Custom memory limit. Defaults to `None`.
- `gen_kwargs (dict, optional)`: Arguments for the case generator. Defaults to an empty dictionary.
- `skip_local_visualization (bool, optional)`: If `True`, skips local visualizations. Defaults to `False`.

**Returns:**
- `Result`: A `Result` object with the evaluation outcome.

---
#### `public_eval`
Evaluates the provided code against the predefined set of public test cases for the current problem.

**Parameters:**
- `code (str)`: The source code to evaluate.
- `code_language (CodeLanguage | str)`: The programming language of the code.
- `judge_version (JudgeVersion | str, optional)`: The judge version. Defaults to `None`.
- `skip_local_visualization (bool, optional)`: If `True`, skips local visualizations. Defaults to `True` for public evaluations.

**Returns:**
- `Result`: A `Result` object detailing the performance on public test cases.

---
#### `private_eval`
Evaluates the provided code against the predefined set of private test cases. This is typically called during the final evaluation step to determine the official score, rank, and performance.

**Parameters:**
- `code (str)`: The source code to evaluate.
- `code_language (CodeLanguage | str)`: The programming language of the code.
- `judge_version (JudgeVersion | str, optional)`: The judge version. Defaults to `None`.

**Returns:**
- `Result`: A `Result` object detailing the performance on private test cases.
- `int`: The new rank achieved with this submission.
- `int`: The new performance score.

---
#### `save`
Saves the current state of the session to a JSON file. This allows the session to be paused and resumed later using `ale_bench.restart(filepath)`.

**Parameters:**
- `filepath (str | os.PathLike, optional)`: The path where the session file will be saved. Defaults to `"session.json"`.

**Returns:**
- `None`

---
#### `close`
Terminates the current session and cleans up all associated resources. This includes stopping the running visualization server and removing the temporary directory used by the current session.

**Parameters:**
- None

**Returns:**
- `None`

### Key Properties

- `problem (Problem)`: Accesses the `Problem` object associated with the session, containing details such as the problem statement and constraints.
- `problem_id (str)`: The ID of the current problem.
- `lite_version (bool)`: Indicates if the session is running in "lite" mode.
- `public_seeds (list[int])`: The list of seeds used for public test cases.
- `num_public_cases (int)`: The number of public test cases.
- `num_private_cases (int)`: The number of private test cases. (Note: `private_seeds` itself is not directly accessible).
- `tool_dir (Path)`: The directory where tools for the current problem are stored.
- `rust_src_dir (Path)`: Path to the source code of Rust-based tools, if applicable.
- `maximum_resource_usage (ResourceUsage)`: The configured maximum resource limits for the session.
- `current_resource_usage (ResourceUsage)`: The current accumulated resource usage.
- `remaining_resource_usage (ResourceUsage)`: The difference between maximum and current resource usage.
- `action_log (list[str])`: A log of all actions performed during the session (e.g., `case_gen`, `public_eval`).
- `session_duration (dt.timedelta)`: The total configured duration for the session.
- `session_started_at (dt.datetime)`: Timestamp of when the session was initiated.
- `session_remaining_time (dt.timedelta)`: The time remaining before the session expires.
- `session_finished (bool)`: Returns `True` if the session has concluded (either by time or resource limits).
- `run_visualization_server (bool)`: Indicates whether the visualization server is active.
- `visualization_server_port (int | None)`: The port number of the visualization server, or `None` if not running.

## Evaluation Example

For fair and reproducible performance comparisons, we **strongly recommend** running evaluations on a consistent, specified AWS instance (e.g., `c6i.32xlarge`).

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

## `RatingCalculator` and `RankingCalculator`

ALE-Bench also provides utilities for calculating ratings and rankings based on contest performance.

### `RatingCalculator`
The `RatingCalculator` class helps estimate a user's rating based on their performance in various contests. It uses a formula similar to the one described in the [official AHC rating document](https://img.atcoder.jp/file/AHC_rating_v2.pdf).

**Initialization:**
```python
from ale_bench.data import RatingCalculator

rating_calculator = RatingCalculator()
```

**Core Method: `calculate_rating`**
Calculates the rating based on a dictionary of performances and the ID of the final contest considered.

**Parameters:**
- `performances (dict[str, int])`: A dictionary where keys are problem IDs (e.g., "ahc001") and values are the performance scores achieved in those problems.
- `final_contest (str)`: The problem ID of the last contest to be included in the rating calculation. Performances from contests ending after this date will be ignored.

**Returns:**
- `int`: The calculated rating, rounded to the nearest integer.

**Example:**
```python
performances = {
    "ahc001": 2000,
    "ahc002": 2200,
    "ahc003": 1800
}
# Assuming ahc003 is the latest contest to consider for this rating calculation
final_rating = rating_calculator.calculate_rating(performances, "ahc003")
print(f"Calculated Rating: {final_rating}")
```

### `RankingCalculator`
The `RankingCalculator` class allows you to determine a user's rank based on their average performance or overall rating, compared against a pre-compiled dataset of existing user rankings. This dataset is automatically downloaded from the Hugging Face Hub.

**Initialization:**
```python
from ale_bench.data import RankingCalculator

# Initialize with a minimum number of contest participations to be included in the ranking pool
# (default is 5)
ranking_calculator = RankingCalculator(minimum_participation=5)
```

**Core Methods:**

#### `calculate_avg_perf_rank`
Calculates the rank based on average performance.

**Parameters:**
- `avg_perf (float)`: The average performance score.

**Returns:**
- `int`: The calculated rank. Lower is better.

#### `calculate_rating_rank`
Calculates the rank based on an overall rating.

**Parameters:**
- `rating (int)`: The overall rating.

**Returns:**
- `int`: The calculated rank. Lower is better.

**Example:**
```python
# Example average performance and rating
my_avg_performance = 2150.75
my_rating = 2345

avg_perf_rank = ranking_calculator.calculate_avg_perf_rank(my_avg_performance)
rating_rank = ranking_calculator.calculate_rating_rank(my_rating)

print(f"Rank based on Average Performance ({my_avg_performance}): {avg_perf_rank}")
print(f"Rank based on Rating ({my_rating}): {rating_rank}")
```

## Cloud Evaluation with AWS

For standardized benchmarking, we leverage [Terraform by HashiCorp](https://www.terraform.io/) to provision a consistent AWS environment.

Consult the [Terraform configuration](./cloud/main.tf), [variables file](./cloud/variables.tf), and [setup script](./cloud/setup.sh) for detailed information. We recommend the use of [Amazon EC2 C6i Instances](https://aws.amazon.com/ec2/instance-types/c6i/) for optimal performance.

**Recommended `num_workers` (parallel evaluations):**
Set `num_workers` to at most the number of **physical cores** of your instance, as most solutions are CPU-bound.

| Instance       | vCPUs | Memory (GiB) | Max `num_workers` | Max `num_workers` (w/ Vis Server) |
|:---------------|:-----:|:------------:|:-----------------:|:---------------------------------:|
| `c6i.xlarge`   | 4     | 8            | 2                 | 1                                 |
| `c6i.2xlarge`  | 8     | 16           | 4                 | 3                                 |
| `c6i.4xlarge`  | 16    | 32           | 8                 | 7                                 |
| `c6i.8xlarge`  | 32    | 64           | 16                | 15                                |
| `c6i.12xlarge` | 48    | 96           | 24                | 23                                |
| `c6i.16xlarge` | 64    | 128          | 32                | 31                                |
| `c6i.24xlarge` | 96    | 192          | 48                | 47                                |
| `c6i.32xlarge` | 128   | 256          | 64                | 63                                |
| `c6i.metal`    | 128   | 256          | 64                | 63                                |


**Workflow:**

1.  **Initialize & Apply Terraform:**
    Before applying, ensure you have an AWS key pair ready. You will need to provide the path to your public key.
    It is also **highly recommended** to restrict SSH access to your IP address for security.
    ```sh
    cd cloud
    terraform init
    terraform apply \
      -var "ssh_public_key_path=</path/to/your/key.pub>" \
      -var "aws_key_name=your-key-pair-name" \
      -var "allowed_ssh_cidr=YOUR_IP_ADDRESS/32" \
      -var "instance_type=c6i.32xlarge" \
      -var "region=us-east-1"
    # Replace </path/to/your/key.pub> with the actual path to your public key.
    # Replace your-key-pair-name with a unique name for the key pair that will be created in AWS.
    # Replace YOUR_IP_ADDRESS/32 with your actual public IP address CIDR (e.g., 123.45.67.89/32).
    # Confirm with 'yes' or use -auto-approve.
    ```
    The `aws_key_name` variable specifies the name of the key pair to be created in AWS using your provided public key. Ensure the corresponding private key is used for SSH access.

2.  **Connect to the EC2 Instance:**
    ```sh
    ssh -i /path/to/your/key.pem ubuntu@<INSTANCE_PUBLIC_IP>
    ```

3.  **Verify Setup:**
    ```sh
    # Check cloud-init logs for successful completion (This setup takes ~10-20 minutes)
    cat /var/log/cloud-init-output.log
    # Look for "ALE-Bench setup completed!" in green text

    # Confirm ALE-Bench directory and activate virtual environment
    ls /home/ubuntu/ALE-Bench
    source /home/ubuntu/ALE-Bench/.venv/bin/activate
    ```

4.  **Terminate Instance:**
    ```sh
    cd cloud # (Run from your local machine, where the terraform state is located)
    terraform destroy -var "ssh_public_key_path=</path/to/your/key.pub>" -var "region=us-east-1"
    # Confirm with 'yes' or use -auto-approve
    ```

## MCP (Model Context Protocol) Server
The MCP server is a lightweight HTTP server that provides a simple interface for interacting with the ALE-Bench toolkit. It allows you to run evaluations and manage sessions without needing to write Python code directly.

### Setup
1. Install Node.js and npm
    ```sh
    # Install nvm (Node Version Manager) for easy Node.js management
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
    # Install the latest LTS version of Node.js
    nvm install --lts
    # Install the Model Context Protocol Inspector
    npm install -g @modelcontextprotocol/inspector
    ```
2. Install the MCP server dependencies using pip or uv:
    ```sh
    cd mcp
    uv sync
    uv sync --extra dev  # For development dependencies
    ```

### Running the MCP Server
```sh
# Ensure you are in the mcp directory (e.g., cd mcp from the project root)
uv run mcp run server.py
uv run mcp dev server.py --with-editable .  # For development
```

### Use with Claude Desktop
1. Open the `claude_desktop_config.json` file that configures the Claude Desktop. Add the following configuration to connect to the MCP server, ensuring you replace `/path/to/ALE-Bench` in the `args` with the actual absolute path to your cloned `ALE-Bench` repository directory:
    ```json
    {
        "mcpServers": {
            "ALE-Bench MCP Server": {
                "command": "/bin/bash",
                "args": [
                    "-c",
                    "cd /path/to/ALE-Bench/mcp && uv run --with ale_bench --with mcp[cli] mcp run /path/to/ALE-Bench/mcp/server.py"
                ]
            }
        }
    }
    ```
2. Restart the Claude Desktop application to apply the changes.

<img width="680" alt="MCP_Claude_Desktop" src="https://github.com/user-attachments/assets/d9f22719-5686-406d-aa94-44406c700d6f" />

## Development

-   **Environment Setup:**
    ```sh
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    pip install ".[dev]"

    # Using uv
    uv venv --python 3.12.9
    uv sync --extra dev
    source .venv/bin/activate
    ```

-   **Docker Image Management:**
    ```sh
    # Build a base image (see scripts/docker_build_base_all.sh)
    # Specify --platform linux/amd64 if building on ARM for x86 compatibility
    docker build ./dockerfiles -t yimjk/ale-bench:python-202301-base -f ./dockerfiles/Dockerfile_python_202301_base

    # Push to Docker Hub (see scripts/docker_push_all.sh)
    docker image push yimjk/ale-bench:python-202301-base

    # Build a user-specific image with correct permissions (see scripts/docker_build_all.sh)
    docker build ./dockerfiles -t ale-bench:python-202301 -f ./dockerfiles/Dockerfile_python_202301 --build-arg UID=$(id -u) --build-arg GID=$(id -g)
    ```
    *Note: When pushing to Docker Hub, please change the image tag prefix `yimjk/` to your own username or organization name as appropriate (e.g., `your-username/ale-bench` or `your-organization/ale-bench`).*

-   **Python Library Development:**
    ```sh
    # Linting
    ruff check src mcp tests

    # Formatting
    ruff format src mcp tests

    # Static Type Checking
    mypy src mcp tests

    # Running Tests
    pytest
    pytest -m "not docker"  # Exclude tests requiring Docker
    ```

## Citation

Please cite ALE-Bench as follows:

```bibtex
@article{imajuku2025ale-bench,
    title={ALE-Bench: A Benchmark for Long-Horizon Objective-Driven Algorithm Engineering},
    author={Imajuku, Yuki and Horie, Kohki and Iwata, Yoichi and Aoki, Kensho and Takahashi, Naohiro and Akiba, Takuya},
    journal={arXiv preprint arXiv:2506.09050},
    year={2025}
}
```
