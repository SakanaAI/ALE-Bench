from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from requests.exceptions import ConnectionError, Timeout

import ale_bench.constants
from ale_bench.code_language import (
    CodeLanguage,
    JudgeVersion,
    get_compile_command,
    get_docker_image_name,
    get_object_file_path,
    get_run_command,
    get_submission_file_path,
)
from ale_bench.data import ProblemType
from ale_bench.result import CaseResult, JudgeResult, Profiles
from ale_bench.utils import docker_client, read_svg


class HostPathsCompile(BaseModel):
    """Paths on the host for the compilation step of the submission."""

    model_config = ConfigDict(frozen=True)

    code_file: Path = Field(description="The code file")
    object_file: Path = Field(description="The object file")


def setup_paths_compile(
    temp_dir: Path,
    code: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
) -> HostPathsCompile:
    """Setup paths for the compilation step of the submission.

    Args:
        temp_dir (Path): The temporary directory.
        code (str): The code to run.
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.

    Returns:
        HostPathsCompile: The paths in the compilation step for the runner tool.
    """
    code_file = temp_dir / get_submission_file_path(code_language, judge_version)
    code_file.parent.mkdir(parents=True, exist_ok=True)
    code_file.write_text(code)
    object_file = temp_dir / get_object_file_path(code_language, judge_version)
    object_file.parent.mkdir(parents=True, exist_ok=True)
    object_file.touch()
    return HostPathsCompile(code_file=code_file, object_file=object_file)


def get_compile_volumes(host_paths: HostPathsCompile, temp_dir: Path) -> dict[str, dict[str, str]]:
    """Get the volumes for the compilation command with the setup.

    Args:
        host_paths (HostPathsCompile): The paths for the runner tool.
        temp_dir (Path): The temporary directory.

    Returns:
        dict[str, dict[str, str]]: The volumes for the compile command with the setup.
    """
    return {
        str(host_paths.code_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.code_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.object_file): {
            "bind": f"/tmp/{host_paths.object_file.relative_to(temp_dir)}",
            "mode": "rw",
        },
    }


def build_compile_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    object_file_relative_path: Path,
) -> str:
    """Build the compile command for the given code language and judge version.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        object_file_relative_path (Path): The relative path of the object file.

    Returns:
        str: The compile command.
    """
    compile_command = get_compile_command(code_language, judge_version)
    compile_command += (
        f"; cp {ale_bench.constants.WORK_DIR}/{object_file_relative_path} /tmp/{object_file_relative_path}"
    )
    compile_command += f"; chmod 744 /tmp/{object_file_relative_path}"
    return compile_command


class HostPathsBatchRun(BaseModel):
    """Paths on the host for the running step of the submission for batch problems."""

    model_config = ConfigDict(frozen=True)

    code_file: Path = Field(description="The code file")
    object_file: Path = Field(description="The object file")
    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    profiles_file: Path = Field(description="The profiles file")


def setup_paths_batch_run(
    host_paths_compile: HostPathsCompile,
    temp_dir: Path,
    input_str: str,
    prefix: str = "",
) -> HostPathsBatchRun:
    """Setup paths for the running step of the submission for batch problems.

    Args:
        host_paths_compile (HostPathsCompile): The paths in the compilation step for the runner tool.
        temp_dir (Path): The temporary directory.
        input_str (str): The input string for the problem.
        prefix (str): The prefix for the input/output/profiles files. Defaults to "".

    Returns:
        HostPathsBatchRun: The paths for the runner tool.
    """
    input_file_name = ale_bench.constants.INPUT_FILE.split("/")[-1]
    input_file = temp_dir / f"{prefix}{input_file_name}"
    input_file.touch()
    input_file.write_text(input_str)
    output_file_name = ale_bench.constants.OUTPUT_FILE.split("/")[-1]
    output_file = temp_dir / f"{prefix}{output_file_name}"
    output_file.touch()
    profiles_file_name = ale_bench.constants.PROFILES_FILE.split("/")[-1]
    profiles_file = temp_dir / f"{prefix}{profiles_file_name}"
    profiles_file.touch()
    return HostPathsBatchRun(
        code_file=host_paths_compile.code_file,
        object_file=host_paths_compile.object_file,
        input_file=input_file,
        output_file=output_file,
        profiles_file=profiles_file,
    )


def get_batch_run_volumes(host_paths: HostPathsBatchRun, temp_dir: Path) -> dict[str, dict[str, str]]:
    """Get the volumes for the run command with the setup.

    Args:
        host_paths (HostPathsRun): The paths for the runner tool.
        temp_dir (Path): The temporary directory.

    Returns:
        dict[str, dict[str, str]]: The volumes for the run command with the setup.
    """
    return {
        str(host_paths.code_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.code_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.object_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.object_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "rw"},
        str(host_paths.profiles_file): {"bind": ale_bench.constants.PROFILES_FILE, "mode": "rw"},
    }


def build_batch_run_command(code_language: CodeLanguage, judge_version: JudgeVersion, time_limit: float) -> str:
    """Build the run command for the given code language and judge version.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        problem_type (ProblemType): The problem type.
        time_limit (float): The time limit in seconds.

    Returns:
        str: The run command.
    """
    run_command = get_run_command(code_language, judge_version)
    run_command += f" < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}"
    run_command = (
        "/usr/bin/time "
        f'-f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" '
        f"-o {ale_bench.constants.PROFILES_FILE} {run_command}"
    )  # NOTE: We use the GNU Time to measure the resource usage
    # NOTE: the profiles by GNU Time update every 1 sec (from observations while debugging)
    time_limit_ceil = math.ceil(time_limit + 0.1)
    run_command = (
        f"timeout {time_limit_ceil + 0.2} "
        f"prlimit --cpu={time_limit_ceil + 0.1} {run_command}"
    )  # NOTE: margin Wall Time: 0.2+α sec, CPU Time: 0.1+α sec
    run_command += "; sync"  # NOTE: Ensure all output is written before the container exits
    return run_command


class HostPathsBatchJudge(BaseModel):
    """Paths on the host for the judging step of the submission for batch problems."""

    model_config = ConfigDict(frozen=True)

    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    profiles_file: Path = Field(description="The profiles file")


def setup_paths_batch_judge(host_paths_batch_run: HostPathsBatchRun) -> HostPathsBatchJudge:
    """Setup paths for the judging step of the submission for batch problems.

    Args:
        host_paths_batch_run (HostPathsBatchRun): The paths for the runner tool.

    Returns:
        HostPathsBatchJudge: The paths for the judging step of the submission.
    """
    return HostPathsBatchJudge(
        input_file=host_paths_batch_run.input_file,
        output_file=host_paths_batch_run.output_file,
        profiles_file=host_paths_batch_run.profiles_file,
    )


def get_batch_judge_volumes(host_paths: HostPathsBatchJudge, tool_dir: Path) -> dict[str, dict[str, str]]:
    """Get the volumes for the judging command with the setup.

    Args:
        host_paths (HostPathsBatchJudge): The paths for the runner tool.
        tool_dir (Path): The directory of the tools.

    Returns:
        dict[str, dict[str, str]]: The volumes for the judging command with the setup.
    """
    return {
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "ro"},
        str(tool_dir / "tools" / "target" / "release" / "tester"): {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
    }


def build_batch_judge_command() -> str:
    """Build the judging command.

    Returns:
        str: The judging command.
    """
    judge_command = (
        f"{ale_bench.constants.TESTER_BIN} {ale_bench.constants.INPUT_FILE} {ale_bench.constants.OUTPUT_FILE}"
    )
    return judge_command


class HostPathsReactiveJudge(BaseModel):
    """Paths on the host for the judging step of the submission for reactive problems."""

    model_config = ConfigDict(frozen=True)

    code_file: Path = Field(description="The code file")
    object_file: Path = Field(description="The object file")
    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    profiles_file: Path = Field(description="The profiles file")


def setup_paths_reactive_judge(
    host_paths_compile: HostPathsCompile,
    temp_dir: Path,
    input_str: str,
    prefix: str = "",
) -> HostPathsReactiveJudge:
    """Setup paths for the judging step of the submission for reactive problems.

    Args:
        host_paths_compile (HostPathsCompile): The paths in the compilation step for the runner tool.
        temp_dir (Path): The temporary directory.
        input_str (str): The input string for the problem.
        prefix (str): The prefix for the input/output/profiles files. Defaults to "".

    Returns:
        HostPathsReactiveJudge: The paths for the runner tool.
    """
    input_file_name = ale_bench.constants.INPUT_FILE.split("/")[-1]
    input_file = temp_dir / f"{prefix}{input_file_name}"
    input_file.touch()
    input_file.write_text(input_str)
    output_file_name = ale_bench.constants.OUTPUT_FILE.split("/")[-1]
    output_file = temp_dir / f"{prefix}{output_file_name}"
    output_file.touch()
    profiles_file_name = ale_bench.constants.PROFILES_FILE.split("/")[-1]
    profiles_file = temp_dir / f"{prefix}{profiles_file_name}"
    profiles_file.touch()
    return HostPathsReactiveJudge(
        code_file=host_paths_compile.code_file,
        object_file=host_paths_compile.object_file,
        input_file=input_file,
        output_file=output_file,
        profiles_file=profiles_file,
    )


def get_reactive_judge_volumes(
    host_paths: HostPathsReactiveJudge, temp_dir: Path, tool_dir: Path
) -> dict[str, dict[str, str]]:
    """Get the volumes for the run command with the setup.

    Args:
        host_paths (HostPathsReactiveJudge): The paths for the runner tool.
        temp_dir (Path): The temporary directory.
        tool_dir (Path): The directory of the tools.

    Returns:
        dict[str, dict[str, str]]: The volumes for the run command with the setup.
    """
    return {
        str(host_paths.code_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.code_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.object_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.object_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "rw"},
        str(host_paths.profiles_file): {"bind": ale_bench.constants.PROFILES_FILE, "mode": "rw"},
        str(tool_dir / "tools" / "target" / "release" / "tester"): {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
    }


def build_reactive_judge_command(code_language: CodeLanguage, judge_version: JudgeVersion, time_limit: float) -> str:
    """Build the run command for the given code language and judge version.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        time_limit (float): The time limit in seconds.

    Returns:
        str: The run command.
    """
    run_command = get_run_command(code_language, judge_version)
    run_command += f" < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}"
    run_command = (
        f"{ale_bench.constants.TESTER_BIN} /usr/bin/time "
        f'-f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" '
        f"-o {ale_bench.constants.PROFILES_FILE} {run_command}"
    )  # NOTE: We use the GNU Time to measure the resource usage
    # NOTE: the profiles by GNU Time update every 1 sec (from observations while debugging)
    time_limit_ceil = math.ceil(time_limit + 0.1)
    run_command = (
        f"timeout {time_limit_ceil + 0.2} "
        f"prlimit --cpu={time_limit_ceil + 0.1} {run_command}"
    )  # NOTE: margin Wall Time: 0.2+α sec, CPU Time: 0.1+α sec
    run_command += "; sync"  # NOTE: Ensure all output is written before the container exits
    return run_command


class HostPathsVis(BaseModel):
    """Paths on the host for the visualization step of the judge."""

    model_config = ConfigDict(frozen=True)

    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    local_visualization_file: Path = Field(description="The local visualization file")


def setup_paths_vis(
    host_paths_judge: HostPathsBatchJudge | HostPathsReactiveJudge, temp_dir: Path, problem_id: str, prefix: str = ""
) -> HostPathsVis:
    """Setup paths for the visualization step of the judge.

    Args:
        host_paths_run (HostPathsBatchRun | HostPathsReactiveRun): The paths for the judge.
        temp_dir (Path): The temporary directory.
        problem_id (str): The problem ID.
        prefix (str): The prefix for the local visualization file. Defaults to "".

    Returns:
        HostPathsVis: The paths for the visualization step of the judge.
    """
    local_visualization_container = (
        ale_bench.constants.LOCAL_VIS_SVG
        if problem_id in ale_bench.constants.VIS_SVG_GENERATION
        else ale_bench.constants.LOCAL_VIS_HTML
    )
    local_visualization_ext = local_visualization_container.rsplit(".", 1)[1]
    local_visualization_file = temp_dir / f"{prefix}local_visualization.{local_visualization_ext}"
    local_visualization_file.touch()
    return HostPathsVis(
        input_file=host_paths_judge.input_file,
        output_file=host_paths_judge.output_file,
        local_visualization_file=local_visualization_file,
    )


def get_vis_volumes(host_paths: HostPathsVis, tool_dir: Path) -> dict[str, dict[str, str]]:
    """Get the volumes for the visualization command with the setup.

    Args:
        host_paths (HostPathsVis): The paths for the runner tool.
        tool_dir (Path): The directory of the tools.

    Returns:
        dict[str, dict[str, str]]: The volumes for the visualization command with the setup.

    Raises:
        ValueError: If the local visualization file does not have a valid extension.
    """
    if host_paths.local_visualization_file.suffix == ".svg":
        local_visualization_container = ale_bench.constants.LOCAL_VIS_SVG
    elif host_paths.local_visualization_file.suffix == ".html":
        local_visualization_container = ale_bench.constants.LOCAL_VIS_HTML
    else:
        raise ValueError("The local visualization file must have either .svg or .html extension.")
    vis_volumes = {
        str(tool_dir / "tools" / "target" / "release" / "vis"): {
            "bind": ale_bench.constants.VIS_BIN,
            "mode": "ro",
        },
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "ro"},
        str(host_paths.local_visualization_file): {"bind": local_visualization_container, "mode": "rw"},
    }
    return vis_volumes


def build_vis_command() -> str:
    """Build the visualization command.

    Returns:
        str: The visualization command.
    """
    vis_command = f"{ale_bench.constants.VIS_BIN} {ale_bench.constants.INPUT_FILE} {ale_bench.constants.OUTPUT_FILE}"
    return vis_command


def run_compile_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    host_paths_compile: HostPathsCompile,
    compile_volumes: dict[str, dict[str, str]],
    compile_command: str,
) -> CaseResult | None:
    """Run the compile command in a Docker container.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        host_paths_compile (ostPathsCompile): The paths for the runner tool in the compilation step.
        compile_volumes (dict[str, dict[str, str]]): The volumes for the compile command with the setup.
        compile_command (str): The compile command.

    Returns:
        CaseResult | None: The case result if the compilation fails, otherwise None.
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
            # NOTE: It will catch ReadTimeout, ConnectTimeout and ConnectionError.
            # NOTE: ConnectionError occurs when the compile code timed out with sleep.
            except (Timeout, ConnectionError):
                if code_language != CodeLanguage.PYTHON:
                    return CaseResult(
                        input_str=None,
                        output_str=None,
                        error_str=None,
                        judge_result=JudgeResult.COMPILATION_ERROR,
                        message=f"Compilation timed out ({ale_bench.constants.COMPILE_TIMEOUT}s).",
                        absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                        execution_time=0.0,
                        memory_usage=0,
                    )
            except Exception:
                return CaseResult(
                    input_str=None,
                    output_str=None,
                    error_str=None,
                    judge_result=JudgeResult.COMPILATION_ERROR,
                    message="Failed to compile the code.",
                    absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                    execution_time=0.0,
                    memory_usage=0,
                )
            # stdout = container.logs(stdout=True, stderr=False).decode("utf-8").strip()
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    object_size = host_paths_compile.object_file.stat().st_size
    if any(
        [
            exit_code != 0,
            # NOTE: As for Python, it is fine if .pyc file is not created during the compilation step.
            code_language != CodeLanguage.PYTHON and object_size == 0,
            # NOTE: We regard SyntaxError as a compilation error for Python
            code_language == CodeLanguage.PYTHON and "SyntaxError" in stderr,
        ]
    ):
        return CaseResult(
            input_str=None,
            output_str=None,
            error_str=None,
            judge_result=JudgeResult.COMPILATION_ERROR,
            message=f"Failed to compile the code.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=0.0,
            memory_usage=0,
        )
    return None  # Compilation succeeded, return None to indicate success


def run_batch_run_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    run_volumes: dict[str, dict[str, str]],
    run_command: str,
    input_str: str | None,
) -> CaseResult | tuple[float, str]:
    """Run the run command in a Docker container for batch problems.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        time_limit (float): The time limit in seconds.
        run_volumes (dict[str, dict[str, str]]): The volumes for the run command with the setup.
        run_command (str): The run command.
        input_str (str | None): The input string of the problem included in the case result.

    Returns:
        CaseResult | tuple[float, str]:
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
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
                memory_usage=0,
            )
        else:
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=execution_time_host,
                memory_usage=0,
            )
    return execution_time_host, stderr  # Run succeeded, return the execution time and stderr


def run_batch_judge_container(
    judge_volumes: dict[str, dict[str, str]],
    judge_command: str,
    execution_time_host: float,
    input_str: str | None,
    output_str: str | None,
    error_str: str | None,
) -> CaseResult | int:
    """Run the run command in a Docker container for batch problems.

    Args:
        judge_volumes (dict[str, dict[str, str]]): The volumes for the judge command with the setup.
        judge_command (str): The judge command.
        execution_time_host (float): The execution time on the host in seconds.
        input_str (str | None): The input string of the problem included in the case result.
        output_str (str | None): The output string of the problem included in the case result.
        error_str (str | None): The error string of the problem included in the case result.

    Returns:
        CaseResult | int: The case result if the judge fails, otherwise the score.
    """
    with docker_client() as client:
        container = client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command=f"/bin/sh -c '{judge_command}'",
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=judge_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            container.wait()  # NOTE: Killed by `timeout` command in the run command
            # stdout = container.logs(stdout=True, stderr=False).decode("utf-8").strip()
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    if "wrong answer: " in stderr:
        error_message = stderr.split("wrong answer: ")[1]
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\n{error_message}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    stderr_last_line = stderr.splitlines()[-1]
    score_match = re.match(r"Score = (\d+)", stderr_last_line)
    if score_match is None:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    score = int(score_match.group(1))
    return score  # Return the score as an integer


def run_reactive_judge_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    judge_volumes: dict[str, dict[str, str]],
    judge_command: str,
    input_str: str | None,
    output_file_path: Path | None,
) -> CaseResult | tuple[float, int, str]:
    """Run the run command in a Docker container for batch problems.

    Args:
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        time_limit (float): The time limit in seconds.
        judge_volumes (dict[str, dict[str, str]]): The volumes for the judge command with the setup.
        judge_command (str): The judge command.
        input_str (str | None): The input string of the problem included in the case result.
        output_file_path (Path | None): The path to the output file. If None, contents of the output file is not used.

    Returns:
        CaseResult | tuple[float, int]: The case result if the run fails,
            otherwise the execution time in seconds, the score and the standard error.
    """
    with docker_client() as client:
        start_at = time.perf_counter()
        container = client.containers.run(
            image=get_docker_image_name(code_language, judge_version),
            command=f"/bin/sh -c '{judge_command}'",
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=judge_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            container.wait()  # NOTE: Killed by `timeout` command in the run command
            end_at = time.perf_counter()
            # stdout = container.logs(stdout=True, stderr=False).decode("utf-8").strip()
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            execution_time_host = end_at - start_at  # NOTE: we use this wall time for `RE` (including the overhead)
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0 or stderr == "":
        if execution_time_host > time_limit:  # Killed by `timeout` command
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
                memory_usage=0,
            )
        else:
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=execution_time_host,
                memory_usage=0,
            )
    stderr_last_line = stderr.splitlines()[-1]
    score_match = re.match(r"Score = (\d+)", stderr_last_line)
    if score_match is None:
        return CaseResult(
            input_str=input_str,
            output_str=output_file_path.read_text() if output_file_path else None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.WRONG_ANSWER,
            message="Wrong answer.",  # NOTE: exclude stderr because we don't want to be exploited by the user
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    score = int(score_match.group(1))
    return (execution_time_host, score, stderr)  # Run succeeded, return the execution time


def run_vis_container(vis_command: str, vis_volumes: dict[str, dict[str, str]]) -> None:
    """Run the visualization command in a Docker container.

    Args:
        vis_command (str): The visualization command.
        vis_volumes (dict[str, dict[str, str]]): The volumes for the visualization command with the setup.
    """
    with docker_client() as client:
        container = client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command=f"/bin/sh -c '{vis_command}'",
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=vis_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            try:
                container.wait(timeout=ale_bench.constants.VISUALIZE_TIMEOUT)
            except Exception:
                raise RuntimeError("Timeout while running the visualization command. Something went wrong.")
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0:
        raise RuntimeError("Failed to run the visualization command. Something went wrong.")


def parse_profiles(
    time_limit: float,
    memory_limit: int,
    profiles_content: str,
    execution_time_host: float,
    input_str: str | None,
    output_str: str | None,
    error_str: str | None,
) -> CaseResult | tuple[float, int]:
    """
    Parse the profiles content and check for time limit, memory limit, and exit status.

    Args:
        time_limit (float): The time limit in seconds.
        memory_limit (int): The memory limit in bytes.
        profiles_content (str): The content of the profiles file.
        execution_time_host (float): The execution time on the host in seconds.
        input_str (str | None): The input string of the problem included in the case result.
        output_str (str | None): The output string of the problem included in the case result.
        error_str (str | None): The error string of the problem included in the case result.

    Returns:
        CaseResult | tuple[float, int]: The case result if there is an error, otherwise (execution_time, memory_usage).
    """
    assert execution_time_host >= 0.0, "execution_time_host must be non-negative"
    # Check if the profiles content is empty or if it indicates a timeout
    is_tle = False
    if profiles_content == "":
        if execution_time_host > time_limit:  # NOTE: ex. `python -c "import time; time.sleep(10)"`
            return CaseResult(
                input_str=input_str,
                output_str=output_str,
                error_str=error_str,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
                memory_usage=0,
            )
        else:  # NOTE: Error in running the code
            return CaseResult(
                input_str=input_str,
                output_str=output_str,
                error_str=error_str,
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
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
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message="Wrong answer.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=0,
        )
    try:
        profiles = Profiles(**profiles_dict)
    except ValueError:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.INTERNAL_ERROR,
            message="Internal Error: Invalid profiles format.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time_host, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=0,
        )  # NOTE: This should not happen, but just in case
    # Check the profiles for exit status, execution time, and memory usage
    exit_status = profiles.exit_status
    execution_time = max(profiles.elapsed_time_seconds, profiles.user_cpu_seconds + profiles.system_cpu_seconds)
    memory_usage = profiles.max_resident_set_size_kbytes * 1024
    # Check the resource usage
    if exit_status != 0:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=memory_usage,
        )
    elif execution_time > time_limit or is_tle:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
            message="Time limit exceeded.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time, time_limit + 0.1),  # NOTE: slight longer than time limit
            memory_usage=memory_usage,
        )
    elif memory_usage > memory_limit:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.MEMORY_LIMIT_EXCEEDED,
            message="Memory limit exceeded.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time,
            memory_usage=memory_usage,
        )
    return execution_time, memory_usage  # Return the execution time and memory usage if all checks pass


def case_iter_func(
    problem_id: str,
    time_limit: float,
    memory_limit: int,
    problem_type: ProblemType,
    case_idx: int,
    input_str: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    temp_dir: Path,
    tool_dir: Path,
    return_details: bool,
    skip_local_visualization: bool,
    host_paths_compile: HostPathsCompile,
    batch_run_command: str,
    batch_judge_command: str,
    reactive_judge_command: str,
    vis_command: str,
) -> CaseResult:
    result_input_str = input_str if return_details else None
    host_paths_judge: HostPathsBatchJudge | HostPathsReactiveJudge
    execution_time_host = -1.0

    if problem_type == ProblemType.BATCH:
        # Run the submission code and generate the output file
        host_paths_run = setup_paths_batch_run(host_paths_compile, temp_dir, input_str, f"{problem_id}_{case_idx:06d}_")
        run_volumes = get_batch_run_volumes(host_paths_run, temp_dir)
        run_result = run_batch_run_container(
            code_language, judge_version, time_limit, run_volumes, batch_run_command, result_input_str
        )
        if isinstance(run_result, CaseResult):
            return run_result
        assert isinstance(run_result, tuple), "Run result must be a tuple"
        execution_time_host, stderr = run_result
        result_output_str = host_paths_run.output_file.read_text() if return_details else None
        result_error_str = stderr if return_details else None
        # Parse the profiles file
        profiles_content = host_paths_run.profiles_file.read_text()
        profiles_result = parse_profiles(
            time_limit,
            memory_limit,
            profiles_content,
            execution_time_host,
            result_input_str,
            result_output_str,
            result_error_str,
        )
        if isinstance(profiles_result, CaseResult):
            return profiles_result  # NOTE: Parsing profiles failed, return the result
        assert isinstance(profiles_result, tuple), "Profiles result must be a tuple"
        execution_time, memory_usage = profiles_result
        # Calculate score by the input and output files
        host_paths_judge = setup_paths_batch_judge(host_paths_run)
        judge_volumes = get_batch_judge_volumes(host_paths_judge, tool_dir)
        batch_judge_result = run_batch_judge_container(
            judge_volumes,
            batch_judge_command,
            execution_time_host,
            result_input_str,
            result_output_str,
            result_error_str,
        )
        if isinstance(batch_judge_result, CaseResult):
            return batch_judge_result
        assert isinstance(batch_judge_result, int), "Judge result must be an integer"
        absolute_score = batch_judge_result
    elif problem_type == ProblemType.REACTIVE:
        host_paths_judge = setup_paths_reactive_judge(
            host_paths_compile,
            temp_dir,
            input_str,
            f"{problem_id}_{case_idx:06d}_",
        )
        judge_volumes = get_reactive_judge_volumes(host_paths_judge, temp_dir, tool_dir)
        reactive_judge_result = run_reactive_judge_container(
            code_language,
            judge_version,
            time_limit,
            judge_volumes,
            reactive_judge_command,
            result_input_str,
            host_paths_judge.output_file if return_details else None,
        )
        wo_profile_result = None
        if isinstance(reactive_judge_result, CaseResult):
            wo_profile_result = reactive_judge_result
            execution_time_host = reactive_judge_result.execution_time  # already processed
            result_output_str = reactive_judge_result.output_str  # already processed
            result_error_str = reactive_judge_result.error_str  # already processed
        else:
            assert isinstance(reactive_judge_result, tuple), "Judge result must be a tuple"
            execution_time_host, absolute_score, stderr = reactive_judge_result
            result_output_str = host_paths_judge.output_file.read_text() if return_details else None
            result_error_str = stderr if return_details else None
        # Parse the profiles file
        profiles_content = host_paths_judge.profiles_file.read_text()
        profiles_result = parse_profiles(
            time_limit,
            memory_limit,
            profiles_content,
            execution_time_host,
            result_input_str,
            result_output_str,
            result_error_str,
        )
        if isinstance(profiles_result, CaseResult):
            return profiles_result  # NOTE: Parsing profiles failed, return the result
        assert isinstance(profiles_result, tuple), "Profiles result must be a tuple"
        execution_time, memory_usage = profiles_result
        if wo_profile_result is not None:
            return CaseResult(
                input_str=wo_profile_result.input_str,
                output_str=wo_profile_result.output_str,
                error_str=wo_profile_result.error_str,
                judge_result=wo_profile_result.judge_result,
                message=wo_profile_result.message,
                absolute_score=wo_profile_result.absolute_score,
                execution_time=execution_time,
                memory_usage=memory_usage,
            )
    else:
        raise ValueError(f"Invalid problem type: {problem_type}")

    # Output the final state and state history if requested
    local_visualization = None
    if not skip_local_visualization and problem_id not in ale_bench.constants.NO_LOCAL_VIS:
        # Run the local visualization command in the Docker container
        host_paths_vis = setup_paths_vis(host_paths_judge, temp_dir, problem_id, f"{problem_id}_{case_idx:06d}_")
        vis_volumes = get_vis_volumes(host_paths_vis, tool_dir)
        run_vis_container(vis_command, vis_volumes)
        # Read the local visualization SVG or HTML
        svg_text = host_paths_vis.local_visualization_file.read_text()
        svg_text = svg_text.replace("\n", "").removeprefix("<html><body>").removesuffix("</body></html>")
        if svg_text == "":
            raise RuntimeError("The local visualization file is empty. Something went wrong.")
        local_visualization = read_svg(svg_text)
    # Add the result
    return CaseResult(
        input_str=result_input_str,
        output_str=result_output_str,
        error_str=result_error_str,
        judge_result=JudgeResult.ACCEPTED,
        message="",
        absolute_score=absolute_score,
        local_visualization=local_visualization,
        execution_time=execution_time,
        memory_usage=memory_usage,
    )


def run_cases(
    inputs: list[str],
    code: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    memory_limit: int,
    problem_id: str,
    problem_type: ProblemType,
    tool_dir: Path,
    return_details: bool,
    skip_local_visualization: bool,
    num_workers: int,
) -> list[CaseResult]:
    """Run the cases for the given inputs and code.

    Args:
        inputs (list[str]): The list of inputs.
        code (str): The code to run.
        code_language (CodeLanguage): The code language.
        judge_version (JudgeVersion): The judge version.
        time_limit (float): The time limit in seconds.
        memory_limit (int): The memory limit in bytes.
        problem_id (str): The problem ID.
        problem_type (ProblemType): The problem type.
        tool_dir (Path): The directory of the tools.
        return_details (bool): Whether to return detailed results (input_str, output_str, error_str).
        skip_local_visualization (bool): Whether to skip local visualization.
        num_workers (int): The number of workers for running cases.

    Returns:
        list[CaseResult]: The list of case results.
    """
    # Temporary directory
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # Prepare for the run
        host_paths_compile = setup_paths_compile(temp_dir, code, code_language, judge_version)
        compile_volumes = get_compile_volumes(host_paths_compile, temp_dir)
        compile_command = build_compile_command(
            code_language, judge_version, host_paths_compile.object_file.relative_to(temp_dir)
        )
        batch_run_command = build_batch_run_command(code_language, judge_version, time_limit)
        batch_judge_command = build_batch_judge_command()
        reactive_judge_command = build_reactive_judge_command(code_language, judge_version, time_limit)
        vis_command = build_vis_command()

        # Compile the code in the Docker container
        compile_result = run_compile_container(
            code_language,
            judge_version,
            host_paths_compile,
            compile_volumes,
            compile_command,
        )
        if compile_result is not None:
            return [compile_result for _ in inputs]  # NOTE: Compilation failed, return the result

        # Run the code and calculate the score in the Docker container
        case_results: list[CaseResult] = []
        if len(inputs) == 1 or num_workers == 1:
            for case_idx, input_str in enumerate(inputs):
                case_result = case_iter_func(
                    problem_id,
                    time_limit,
                    memory_limit,
                    problem_type,
                    case_idx,
                    input_str,
                    code_language,
                    judge_version,
                    temp_dir,
                    tool_dir,
                    return_details,
                    skip_local_visualization,
                    host_paths_compile,
                    batch_run_command,
                    batch_judge_command,
                    reactive_judge_command,
                    vis_command,
                )
                # Add the result
                case_results.append(case_result)
        else:
            case_results = [
                CaseResult(
                    input_str=input_str if return_details else None,
                    output_str=None,
                    error_str=None,
                    judge_result=JudgeResult.INTERNAL_ERROR,
                    message="Internal Error: Unexpected error occurred.",
                    absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                    execution_time=0.0,
                    memory_usage=0,
                )
                for input_str in inputs
            ]
            # Use ThreadPoolExecutor to run the cases in parallel
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                future_to_case_idx = {}
                for case_idx, input_str in enumerate(inputs):
                    future = executor.submit(
                        case_iter_func,
                        problem_id,
                        time_limit,
                        memory_limit,
                        problem_type,
                        case_idx,
                        input_str,
                        code_language,
                        judge_version,
                        temp_dir,
                        tool_dir,
                        return_details,
                        skip_local_visualization,
                        host_paths_compile,
                        batch_run_command,
                        batch_judge_command,
                        reactive_judge_command,
                        vis_command,
                    )
                    future_to_case_idx[future] = case_idx
                for future in as_completed(future_to_case_idx):
                    case_idx = future_to_case_idx[future]
                    try:
                        case_result = future.result()
                    except Exception as e:
                        case_result = CaseResult(
                            input_str=inputs[case_idx] if return_details else None,
                            output_str=None,
                            error_str=None,
                            judge_result=JudgeResult.INTERNAL_ERROR,
                            message=f"Internal Error: {e}",
                            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                            execution_time=0.0,
                            memory_usage=0,
                        )
                    case_results[case_idx] = case_result

    return case_results
