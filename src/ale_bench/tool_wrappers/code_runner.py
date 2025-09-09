from __future__ import annotations

import enum
import json
import os
import tempfile
import time
from pathlib import Path

from requests.exceptions import ConnectionError, Timeout

import ale_bench.constants
from ale_bench.code_language import (
    CodeLanguage,
    JudgeVersion,
    get_docker_image_name,
)
from ale_bench.result import CodeRunResult, Profiles
from ale_bench.tool_wrappers.case_runner import (
    HostPathsCompile,
    build_batch_run_command,
    build_compile_command,
    get_batch_run_volumes,
    get_compile_volumes,
    setup_paths_batch_run,
    setup_paths_compile,
)
from ale_bench.utils import docker_client


class ExitStatus(enum.IntEnum):
    """Exit status codes."""

    SUCCESS = 0
    COMPILE_ERROR = -1
    RUNTIME_ERROR = 1
    TIME_LIMIT_EXCEEDED = 9
    MEMORY_LIMIT_EXCEEDED = 9


def run_compile_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    host_paths_compile: HostPathsCompile,
    compile_volumes: dict[str, dict[str, str]],
    compile_command: str,
) -> CodeRunResult | None:
    """Run the compile command in a Docker container.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        host_paths_compile (ostPathsCompile): The paths for the runner tool in the compilation step.
        compile_volumes (dict[str, dict[str, str]]): The volumes for the compile command with the setup.
        compile_command (str): The compile command.

    Returns:
        CodeRunResult | None: The case result if the compilation fails, otherwise None.
    """
    with docker_client() as client:
        container = client.containers.run(
            image=get_docker_image_name(code_language, judge_version),
            command=f"/bin/sh -c '{compile_command}'",
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=compile_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            try:
                container.wait(timeout=ale_bench.constants.COMPILE_TIMEOUT)
            except (Timeout, ConnectionError):
                if code_language != CodeLanguage.PYTHON:
                    return CodeRunResult(
                        stdin="",
                        stdout="",
                        stderr=f"Compilation timed out ({ale_bench.constants.COMPILE_TIMEOUT}s).",
                        exit_status=ExitStatus.COMPILE_ERROR.value,
                        execution_time=0.0,
                        memory_usage=0,
                    )
            except Exception:
                return CodeRunResult(
                    stdin="",
                    stdout="",
                    stderr="Failed to compile the code due to an unexpected error.",
                    exit_status=ExitStatus.COMPILE_ERROR.value,
                    execution_time=0.0,
                    memory_usage=0,
                )
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    object_size = host_paths_compile.object_file.stat().st_size
    if any(
        [
            exit_code != 0,
            code_language != CodeLanguage.PYTHON and object_size == 0,
            code_language == CodeLanguage.PYTHON and "SyntaxError" in stderr,
        ]
    ):
        return CodeRunResult(
            stdin="",
            stdout="",
            stderr=stderr,
            exit_status=ExitStatus.COMPILE_ERROR.value,
            execution_time=0.0,
            memory_usage=0,
        )
    return None  # Compilation succeeded, return None to indicate success


def run_run_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    run_volumes: dict[str, dict[str, str]],
    run_command: str,
    stdin: str,
) -> CodeRunResult | tuple[float, str]:
    """Run the run command in a Docker container for batch problems.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        time_limit (float): The time limit in seconds.
        run_volumes (dict[str, dict[str, str]]): The volumes for the run command with the setup.
        run_command (str): The run command.
        stdin (str): The input string of the problem included in the case result.

    Returns:
        CodeRunResult | tuple[float, str]:
            The case result if the run fails, otherwise the execution time in seconds and the standard error.
    """
    with docker_client() as client:
        start_at = time.perf_counter()
        container = client.containers.run(
            image=get_docker_image_name(code_language, judge_version),
            command=f"/bin/sh -c '{run_command}'",
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=run_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            container.wait()  # NOTE: Killed by `timeout` command in the run command
            end_at = time.perf_counter()
            execution_time_host = end_at - start_at  # NOTE: we use this wall time for `RE` (including the overhead)
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0:
        if execution_time_host > time_limit:  # Killed by `timeout` command
            return CodeRunResult(
                stdin=stdin,
                stdout="",
                stderr=stderr,
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
                memory_usage=0,
            )
        else:
            return CodeRunResult(
                stdin=stdin,
                stdout="",
                stderr=stderr,
                exit_status=exit_code,
                execution_time=execution_time_host,
                memory_usage=0,
            )
    return execution_time_host, stderr  # Run succeeded, return the execution time and stderr


def parse_profiles(
    time_limit: float,
    memory_limit: int,
    profiles_content: str,
    execution_time_host: float,
    stdin: str,
    stdout: str,
    stderr: str,
) -> CodeRunResult | tuple[float, int]:
    """
    Parse the profiles content and check for time limit, memory limit, and exit status.

    Args:
        time_limit (float): The time limit in seconds.
        memory_limit (int): The memory limit in bytes.
        profiles_content (str): The content of the profiles file.
        execution_time_host (float): The execution time on the host in seconds.
        stdin (str): The input string of the problem included in the case result.
        stdout (str | None): The output string of the problem included in the case result.
        stderr (str | None): The error string of the problem included in the case result.

    Returns:
        CodeRunResult | tuple[float, int]:
            The code run result if there is an error, otherwise (execution_time, memory_usage).
    """
    assert execution_time_host >= 0.0, "execution_time_host must be non-negative"
    # Check if the profiles content is empty or if it indicates a timeout
    is_tle = False
    if profiles_content == "":
        if execution_time_host > time_limit:  # NOTE: ex. `python -c "import time; time.sleep(10)"`
            return CodeRunResult(
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
                memory_usage=0,
            )
        else:  # NOTE: Error in running the code
            return CodeRunResult(
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=execution_time_host,
                memory_usage=0,
            )
    elif profiles_content.startswith("Command terminated by signal 9"):
        # NOTE: Sigkill is sent by `prlimit` and included to the profiles file
        profiles_content = profiles_content.split("\n", 1)[1]  # Remove the first line
        is_tle = True
    elif profiles_content.startswith("Command exited with non-zero status"):
        # NOTE: This indicates that the run command failed
        profiles_content = profiles_content.split("\n", 1)[1]  # Remove the first line
    # Parse the profiles content
    profiles_content = profiles_content.strip()
    try:
        profiles_dict = json.loads(profiles_content)
    except json.JSONDecodeError:
        return CodeRunResult(
            stdin=stdin,
            stdout=stdout,
            stderr=f"Failed to parse profiles.\nStandard error:\n{stderr}",
            exit_status=ExitStatus.RUNTIME_ERROR.value,
            execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=0,
        )
    try:
        profiles = Profiles(**profiles_dict)
    except ValueError:
        return CodeRunResult(
            stdin=stdin,
            stdout=stdout,
            stderr=f"Invalid profiles format.\nStandard error:\n{stderr}",
            exit_status=ExitStatus.RUNTIME_ERROR.value,
            execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=0,
        )  # NOTE: This should not happen, but just in case
    # Check the profiles for exit status, execution time, and memory usage
    exit_status = profiles.exit_status
    execution_time = max(profiles.elapsed_time_seconds, profiles.user_cpu_seconds + profiles.system_cpu_seconds)
    memory_usage = profiles.max_resident_set_size_kbytes * 1024
    # Check the resource usage
    if exit_status != 0:
        return CodeRunResult(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            exit_status=exit_status,
            execution_time=min(execution_time, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=memory_usage,
        )
    elif execution_time > time_limit or is_tle:
        return CodeRunResult(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
            execution_time=min(execution_time, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=memory_usage,
        )
    elif memory_usage > memory_limit:
        return CodeRunResult(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            exit_status=ExitStatus.MEMORY_LIMIT_EXCEEDED.value,
            execution_time=execution_time,
            memory_usage=memory_usage,
        )
    return execution_time, memory_usage  # Return the execution time and memory usage if all checks pass


def run_code(
    *,
    code: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    stdin: str,
    time_limit: float,
    memory_limit: int,
) -> CodeRunResult:
    """Run the given code with the specified language and judge version.

    Args:
        code (str): The code to run.
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        stdin (str): The input string to be provided to the program.
        time_limit (float): The time limit in seconds.
        memory_limit (int): The memory limit in bytes.

    Returns:
        CodeRunResult: The result of the code execution.
    """
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        # Compilation
        host_paths_compile = setup_paths_compile(temp_dir, code, code_language, judge_version)
        compile_volumes = get_compile_volumes(host_paths_compile, temp_dir)
        compile_command = build_compile_command(
            code_language, judge_version, host_paths_compile.object_file.relative_to(temp_dir)
        )
        compile_result = run_compile_container(
            code_language,
            judge_version,
            host_paths_compile,
            compile_volumes,
            compile_command,
        )
        if compile_result is not None:
            return compile_result
        # Running
        host_paths_run = setup_paths_batch_run(host_paths_compile, temp_dir, stdin)
        run_volumes = get_batch_run_volumes(host_paths_run, temp_dir)
        run_command = build_batch_run_command(code_language, judge_version, time_limit)
        run_result = run_run_container(code_language, judge_version, time_limit, run_volumes, run_command, stdin)
        if isinstance(run_result, CodeRunResult):
            return run_result
        assert isinstance(run_result, tuple), "Run result must be a tuple"
        execution_time_host, stderr = run_result
        stdout = host_paths_run.output_file.read_text()
        # Parse the profiles file
        profiles_content = host_paths_run.profiles_file.read_text()
        profiles_result = parse_profiles(
            time_limit,
            memory_limit,
            profiles_content,
            execution_time_host,
            stdin,
            stdout,
            stderr,
        )
        if isinstance(profiles_result, CodeRunResult):
            return profiles_result  # NOTE: Parsing profiles failed, return the result
        assert isinstance(profiles_result, tuple), "Profiles result must be a tuple"
        execution_time, memory_usage = profiles_result

        return CodeRunResult(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            exit_status=ExitStatus.SUCCESS.value,
            execution_time=execution_time,
            memory_usage=memory_usage,
        )
