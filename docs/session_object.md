# `Session` Object

The `Session` object is central to ALE-Bench, encapsulating the state and functionalities for an evaluation session on a specific problem. It facilitates input case generation, code execution, visualization, and evaluation.

## Initialization

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

## Core Methods

Each method is described below with its parameters and return values.

### `code_run`
Compiles (if needed) and runs arbitrary code inside the language-specific Docker image. No judging or visualization is performed.

**Parameters:**
- `input_str (str)`: Standard input to the program.
- `code (str)`: The source code to run.
- `code_language (CodeLanguage | str)`: The programming language of the code. Can be a `CodeLanguage` enum member or its string representation (e.g., "python", "cpp17").
- `judge_version (JudgeVersion | str, optional)`: The version of the judge to use. Defaults to `None` (uses the latest or problem-specific default).
- `time_limit (float, optional)`: Custom time limit for execution in seconds. Defaults to `None` (uses problem-specific default).
- `memory_limit (int | str, optional)`: Custom memory limit for execution (e.g., `256_000_000` for 256MB, or "256m"). Defaults to `None` (uses problem-specific default).

**Returns:**
- `CodeRunResult`: A `CodeRunResult` object containing the standard input, output, error, exit status, execution time, and memory usage for the code run.

---
### `case_gen`
Generates input case(s) based on the provided seed(s) and generation arguments.

**Parameters:**
- `seed (list[int] | int, optional)`: The seed or list of seeds for case generation. Defaults to `0`.
- `gen_kwargs (dict, optional)`: Dictionary of arguments for the case generator. Defaults to an empty dictionary.

**Returns:**
- `list[str] | str`: The generated case(s) as string(s). Returns a single string if `seed` is an `int`, or a list of strings if `seed` is a `list[int]`.

---
### `case_eval`
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
### `case_gen_eval`
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
### `local_visualization`
Creates local visualization(s) of the provided input string(s) and output string(s).

**Parameters:**
- `input_str (list[str] | str)`: The input string(s) to visualize.
- `output_str (list[str] | str)`: The output string(s) to visualize.

**Returns:**
- `list[Image.Image | None] | Image.Image | None`: The generated visualization(s) as Pillow `Image` object(s). Returns `None` if the problem does not support local visualization or if an error occurs (mainly due to the `output_str` being invalid).

---
### `public_eval`
Evaluates the provided code against the predefined set of public test cases for the current problem.

**Parameters:**
- `code (str)`: The source code to evaluate.
- `code_language (CodeLanguage | str)`: The programming language of the code.
- `judge_version (JudgeVersion | str, optional)`: The judge version. Defaults to `None`.
- `skip_local_visualization (bool, optional)`: If `True`, skips local visualizations. Defaults to `True` for public evaluations.

**Returns:**
- `Result`: A `Result` object detailing the performance on public test cases.

---
### `private_eval`
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
### `save`
Saves the current state of the session to a JSON file. This allows the session to be paused and resumed later using `ale_bench.restart(filepath)`.

**Parameters:**
- `filepath (str | os.PathLike, optional)`: The path where the session file will be saved. Defaults to `"session.json"`.

**Returns:**
- `None`

---
### `close`
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
