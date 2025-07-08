from __future__ import annotations

import datetime as dt
import json
import math
import os
import warnings
from pathlib import Path

from ale_bench.data import build_rust_tools, list_problem_ids, load_problem
from ale_bench.error import AleBenchError
from ale_bench.result import ResourceUsage
from ale_bench.session import Session
from ale_bench.utils import find_free_port, get_cache_dir


def start(
    problem_id: str,
    lite_version: bool = False,
    use_same_time_scale: bool = False,
    maximum_num_case_gen: int = int(1e18),
    maximum_num_case_eval: int = int(1e18),
    maximum_execution_time_case_eval: float = 1e18,
    maximum_num_call_public_eval: int = int(1e18),
    session_duration: dt.timedelta | int | float | None = None,
    num_workers: int = 1,
    run_visualization_server: bool = False,
    visualization_server_port: int | None = None,
) -> Session:
    """Start a new session for the given problem ID.

    Args:
        problem_id (str): The ID of the problem to start a session for.
        lite_version (bool): Whether to use the lite version. Defaults to False.
        use_same_time_scale (bool, optional): Whether to use the same time scale for the simulation. Defaults to False.
        maximum_num_case_gen (int, optional): Maximum number of generated cases. Defaults to 1e18.
        maximum_num_case_eval (int, optional): Maximum number of evaluated cases. Defaults to 1e18.
        maximum_execution_time_case_eval (float, optional): Maximum execution time of case evaluation. Defaults to 1e18.
        maximum_num_call_public_eval (int, optional): Maximum number of public evaluation calls. Defaults to 1e18.
        session_duration (dt.timedelta | int | float, optional): The duration of the session. Defaults to None.
        num_workers (int, optional): The number of workers to run the judge in parallel. Defaults to 1.
        run_visualization_server (bool, optional): Whether to run the visualization server. Defaults to False.
        visualization_server_port (int | None, optional): The port for the visualization server. Defaults to None.
            If None and `run_visualization_server` is True, a free port (9000-65535) will be used.

    Returns:
        Session: The session object for the given problem ID.

    Raises:
        AleBenchError: If the problem ID is not found.
    """

    # Configure the cache directory
    cache_dir = get_cache_dir()
    if not cache_dir.is_dir():
        print(f"Creating cache directory: {cache_dir}")
        cache_dir.mkdir(parents=True)

    # Check if the problem ID exists
    if problem_id not in list_problem_ids(lite_version=lite_version):
        raise AleBenchError(f"Problem ID {problem_id} not found.")

    # Load the dataset
    problem, seeds, standings, rank_performance_map, data_root = load_problem(problem_id, lite_version)

    # Build the Rust tools
    build_rust_tools(data_root / "tools")

    # Set maximum resource usage if not provided
    num_call_public_eval = (
        math.floor(problem.metadata.duration.total_seconds()) // problem.metadata.submission_interval_seconds
    )
    maximum_resource_usage = ResourceUsage(
        num_case_gen=maximum_num_case_gen,
        num_case_eval=maximum_num_case_eval,
        num_call_public_eval=num_call_public_eval if use_same_time_scale else maximum_num_call_public_eval,
        num_call_private_eval=1,  # NOTE: We only allow one private evaluation
        execution_time_case_eval=maximum_execution_time_case_eval,
    )

    # Set session duration if not provided
    if session_duration is None:
        session_duration = problem.metadata.duration
    else:
        if isinstance(session_duration, (int, float)):
            session_duration = dt.timedelta(seconds=session_duration)

    # Set the visualization server port if not provided
    if run_visualization_server:
        if visualization_server_port is None:
            visualization_server_port = find_free_port(min_port=9000, max_port=65535)
    else:
        visualization_server_port = None  # None means no visualization server

    # Create a new session for the problem
    # NOTE: We only use 5 public seeds and 10% of private seeds for the lite version
    session = Session(
        problem=problem,
        lite_version=lite_version,
        public_seeds=seeds.public,
        private_seeds=seeds.private,
        standings=standings,
        rank_performance_map=rank_performance_map,
        tool_dir=data_root,
        use_same_time_scale=use_same_time_scale,
        maximum_resource_usage=maximum_resource_usage,
        session_duration=session_duration,
        num_workers=num_workers,
        visualization_server_port=visualization_server_port,
    )

    return session


def restart(
    session_saved_file: str | os.PathLike[str],
    num_workers: int | None = None,
    visualization_server_port: int | None = None,
) -> Session:
    """Restart a session from a saved file.

    Args:
        session_saved_file (str | os.PathLike[str]): The path to the saved session file.
        num_workers (int, optional): The number of workers to run the judge in parallel. Defaults to 1.
        visualization_server_port (int | None, optional): The port for the visualization server. Defaults to None.
            If None, the port from the saved session will be used if saved session used the visualization server.

    Returns:
        Session: The restarted session object.

    Warnings:
        - If the number of workers in the saved session is different from the provided one.
        - If the saved session did not use the visualization server but the new session will use it.
    """
    session_data = json.loads(Path(session_saved_file).read_text())

    # Load the dataset
    problem, seeds, standings, rank_performance_map, data_root = load_problem(
        session_data["problem_id"], session_data["lite_version"]
    )

    # Build the Rust tools
    build_rust_tools(data_root / "tools")

    # Check the `num_workers` argument and warn if it is different from the saved session
    if num_workers is None:
        num_workers = session_data["num_workers"]
    elif num_workers != session_data["num_workers"]:
        warnings.warn(
            f"Number of workers in the saved session ({session_data['num_workers']}) "
            f"is different from the provided one ({num_workers})."
        )

    # Set the visualization server port if not provided
    if visualization_server_port is None:
        visualization_server_port = session_data["visualization_server_port"]
    elif session_data["visualization_server_port"] is None:
        warnings.warn("The saved session did not use the visualization server but the new session will use it.")

    # Create a new session for the problem
    session = Session(
        problem=problem,
        lite_version=session_data["lite_version"],
        public_seeds=seeds.public,
        private_seeds=seeds.private,
        standings=standings,
        rank_performance_map=rank_performance_map,
        tool_dir=data_root,
        use_same_time_scale=session_data["use_same_time_scale"],
        maximum_resource_usage=ResourceUsage.model_validate(session_data["maximum_resource_usage"]),
        session_duration=dt.timedelta(seconds=session_data["session_duration"]),
        num_workers=num_workers,
        visualization_server_port=visualization_server_port,
    )

    session._current_resource_usage = ResourceUsage.model_validate(session_data["current_resource_usage"])
    session._action_log = session_data["action_log"]

    session._session_started_at -= dt.datetime.fromtimestamp(
        session_data["session_paused_at"]
    ) - dt.datetime.fromtimestamp(
        session_data["session_started_at"]
    )  # NOTE: We need to subtract the duration time already passed
    if session_data["last_public_eval_time"] >= session_data["session_started_at"]:
        session._last_public_eval_time = session._session_started_at + dt.timedelta(
            seconds=session_data["last_public_eval_time"] - session_data["session_started_at"]
        )
    if session_data["last_private_eval_time"] >= session_data["session_started_at"]:
        session._last_private_eval_time = session._session_started_at + dt.timedelta(
            seconds=session_data["last_private_eval_time"] - session_data["session_started_at"]
        )
    return session
