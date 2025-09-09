from __future__ import annotations

import atexit
import datetime as dt
import json
import os
import shutil
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn

from PIL import Image

import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.data import Problem, RankPerformanceMap, Standings, start_visualization_server
from ale_bench.error import AleBenchError
from ale_bench.result import CaseResult, CodeRunResult, ResourceUsage, Result
from ale_bench.tool_wrappers import generate_inputs, local_visualization, run_cases, run_code
from ale_bench.utils import docker_client


class AleBenchFunction(str, Enum):
    """Functions for ALE-Bench."""

    CODE_RUN = "code_run"
    CASE_GEN = "case_gen"
    CASE_EVAL = "case_eval"
    CASE_GEN_EVAL = "case_gen_eval"
    PUBLIC_EVAL = "public_eval"
    PRIVATE_EVAL = "private_eval"


CHECK_RESOURCE_USAGE_FIELDS = {
    AleBenchFunction.CODE_RUN: {"execution_time_case_eval"},
    AleBenchFunction.CASE_GEN: {"num_case_gen"},
    AleBenchFunction.CASE_EVAL: {"num_case_eval", "execution_time_case_eval"},
    AleBenchFunction.CASE_GEN_EVAL: {"num_case_gen", "num_case_eval", "execution_time_case_eval"},
    AleBenchFunction.PUBLIC_EVAL: {"num_call_public_eval"},
    AleBenchFunction.PRIVATE_EVAL: {"num_call_private_eval"},
}


class Session:
    """A class representing a session for a given problem ID."""

    def __init__(
        self,
        problem: Problem,
        lite_version: bool,
        public_seeds: list[int],
        private_seeds: list[int],
        standings: Standings,
        rank_performance_map: RankPerformanceMap,
        tool_dir: Path,
        use_same_time_scale: bool,
        maximum_resource_usage: ResourceUsage,
        session_duration: dt.timedelta,
        num_workers: int,
        visualization_server_port: int | None,
    ) -> None:
        """Initialize a new session for the given problem ID.

        Args:
            problem (Problem): The problem object for the session.
            lite_version (bool): Whether to use the lite version of seeds.
            public_seeds (list[int]): The public seeds for the session.
            private_seeds (list[int]): The private seeds for the session.
            standings (Standings): The standings for the session.
            rank_performance_map (RankPerformanceMap): The rank performance map for the session.
            tool_dir (Path): The directory for the tools.
            use_same_time_scale (bool): Whether to use the same time scale for simulating the contest.
            maximum_resource_usage (ResourceUsage): The maximum resource usage for the session.
            session_duration (dt.timedelta): The duration of the session.
            num_workers (int): The number of workers for the `run_cases` function.
            visualization_server_port (int | None): The port number for the visualization server.
                If None, the server will not be started.

        Raises:
            AleBenchError: If failed to initialize the public / private inputs or start the visualization server.
        """
        # NOTE: We use private attributes to prevent modification of the session (but it's not perfect)
        self._problem = problem
        self._lite_version = lite_version
        self._public_seeds = public_seeds
        self._private_seeds = private_seeds
        self._standings = standings
        self._rank_performance_map = rank_performance_map
        self._tool_dir = tool_dir
        self._use_same_time_scale = use_same_time_scale
        self._maximum_resource_usage = maximum_resource_usage
        self._session_duration = session_duration
        self._run_visualization_server = visualization_server_port is not None
        self._visualization_server_port = visualization_server_port
        self.num_workers = num_workers  # NOTE: You can change the number of workers for the `run_cases` function

        self._current_resource_usage = ResourceUsage()
        self._action_log: list[str] = []
        self._last_public_eval_time = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        self._last_private_eval_time = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

        self._public_inputs = generate_inputs(public_seeds, {}, tool_dir)
        if len(self._public_inputs) != len(public_seeds):
            raise AleBenchError("Failed to initialize: generating public inputs failed.")
        self._private_inputs = generate_inputs(private_seeds, {}, tool_dir)
        if len(self._private_inputs) != len(private_seeds):
            raise AleBenchError("Failed to initialize: generating private inputs failed.")

        # Start the visualization server if needed
        self._visualization_server_container_id = None
        if visualization_server_port is not None:
            try:
                self._visualization_server_container_id = start_visualization_server(
                    visualization_server_dir=tool_dir / "visualization_server",
                    port_num=visualization_server_port,
                )
            except Exception as e:
                raise AleBenchError(f"Failed to start the visualization server: {e}")

        # Register the cleanup function to be called on exit
        atexit.register(self.close)

        # Set the session started time
        self._session_started_at = dt.datetime.now(tz=dt.timezone.utc)

    def __repr__(self) -> str:
        return f"Session(problem_id={self.problem_id})"

    # Interface
    def code_run(
        self,
        input_str: str,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
    ) -> CodeRunResult:
        """Run arbitrary code with input and return stdout, stderr, exit status, time, and memory.

        This endpoint compiles (if needed) and runs the given code inside the language-specific Docker image.
        It does NOT perform judging or visualization.

        Args:
            input_str (str): Standard input passed to the program.
            code (str): Source code to run.
            code_language (CodeLanguage | str): Language of the source code.
            judge_version (JudgeVersion | str | None): Toolchain version (e.g., 201907/202301). Defaults to 202301.
            time_limit (float | None): CPU/timeout limit in seconds. Defaults to the problem's time limit.
            memory_limit (int | str | None): Memory limit in bytes. Defaults to the problem's memory limit.

        Returns:
            CodeRunResult: Run outputs and resource usage. Status code does NOT match the original AtCoder status code.

        Raises:
            AleBenchError: If the session has finished or arguments are invalid.
        """
        # Preprocessing
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        if not self._check_within_resource_usage_before(AleBenchFunction.CODE_RUN):
            raise AleBenchError("The resource usage is exceeded.")
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        (input_list, code, code_language, judge_version, time_limit, memory_limit) = self._check_run_cases_arguments(
            input_str=input_str,
            allow_empty_input=True,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )
        assert len(input_list) == 1

        # Run
        result = run_code(
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            stdin=input_list[0],
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

        # Resource usage update (execution time only)
        resource_usage = ResourceUsage(execution_time_case_eval=result.execution_time)
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.CODE_RUN):
            raise AleBenchError("The resource usage is exceeded after the action.")

        # Save the action log and return the result
        self._action_log.append(
            json.dumps(
                {
                    "function": "code_run",
                    "arguments": {
                        "input_str": input_str,
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                        "time_limit": time_limit,
                        "memory_limit": memory_limit,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return result

    def case_gen(self, seed: list[int] | int = 0, gen_kwargs: dict[str, Any] = {}) -> list[str] | str:
        """Generate a case using the given seed and generation arguments.

        Args:
            seed (list[int] | int, optional): The seed(s) for the case generation. Defaults to 0.
            gen_kwargs (dict[str, Any]): The generation arguments. Defaults to an empty dictionary.

        Returns:
            list[str] | str: The generated case(s). If `seed` is a list, returns a list of cases.

        Raises:
            AleBenchError: If the session is finished, the resource usage is exceeded, or the generation fails.
        """
        # Preprocessing
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        if not self._check_within_resource_usage_before(AleBenchFunction.CASE_GEN):
            raise AleBenchError("The resource usage is exceeded.")
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        is_scalar = isinstance(seed, int)
        seed, gen_kwargs = self._check_input_generation_arguments(seed=seed, gen_kwargs=gen_kwargs)

        # Generation
        generated_cases = generate_inputs(seed, gen_kwargs, self._tool_dir)

        # Postprocessing
        if len(generated_cases) == 0:
            raise AleBenchError("Failed to generate the case. Maybe you specified invalid arguments.")
        if len(generated_cases) != len(seed):
            raise AleBenchError(
                "Something went wrong: The number of generated cases must match the number of seeds provided."
            )
        self._current_resource_usage = self._current_resource_usage + ResourceUsage(num_case_gen=len(generated_cases))
        if not self._check_within_resource_usage_after(AleBenchFunction.CASE_GEN):
            raise AleBenchError("The resource usage is exceeded after the action.")

        # Save the action log and return the result
        self._action_log.append(
            json.dumps(
                {
                    "function": "case_gen",
                    "arguments": {"seed": seed, "gen_kwargs": gen_kwargs},
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return generated_cases[0] if is_scalar else generated_cases

    def case_eval(
        self,
        input_str: list[str] | str,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
        skip_local_visualization: bool = False,
    ) -> Result:
        """Evaluate the code with the given input.

        We assume this action is a local evaluation, so you can set the time limit and memory limit.

        Args:
            input_str (list[str] | str): The input string(s) for the evaluation.
            code (str): The code to evaluate.
            code_language (CodeLanguage | str): The code language.
            judge_version (JudgeVersion | str, optional): The judge version. Defaults to None.
            time_limit (float, optional): The time limit in seconds. Defaults to None.
            memory_limit (int | str, optional): The memory limit in bytes. Defaults to None.
            skip_local_visualization (bool, optional): Whether to skip local visualization. Defaults to False.

        Returns:
            Result: The result of the evaluation.

        Raises:
            AleBenchError: If the session is finished or the resource usage is exceeded.
            AssertionError: If the number of case results is not 1.
        """
        # Preprocessing
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        if not self._check_within_resource_usage_before(AleBenchFunction.CASE_EVAL):
            raise AleBenchError("The resource usage is exceeded.")
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        (input_str, code, code_language, judge_version, time_limit, memory_limit) = self._check_run_cases_arguments(
            input_str=input_str,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

        # Evaluation
        case_results = run_cases(
            inputs=input_str,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
            problem_id=self._problem.metadata.problem_id,
            problem_type=self._problem.metadata.problem_type,
            tool_dir=self._tool_dir,
            return_details=True,
            skip_local_visualization=skip_local_visualization,
            num_workers=self.num_workers,
        )

        # Postprocessing
        assert len(case_results) == len(input_str), (
            "The number of case results must be equal to the number of input strings."
        )
        resource_usage = ResourceUsage(
            num_case_eval=len(case_results),
            execution_time_case_eval=sum([case_result.execution_time for case_result in case_results]),
        )
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.CASE_EVAL):
            raise AleBenchError("The resource usage is exceeded after the action.")

        # Save the action log and return the result
        self._action_log.append(
            json.dumps(
                {
                    "function": "case_eval",
                    "arguments": {
                        "input_str": input_str,
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                        "time_limit": time_limit,
                        "memory_limit": memory_limit,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return Result(
            allow_score_non_ac=True,  # NOTE: This is a local evaluation, so we return sum of scores even if it's not AC
            resource_usage=resource_usage,
            case_results=case_results,
        )

    def case_gen_eval(
        self,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        seed: list[int] | int = 0,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
        gen_kwargs: dict[str, Any] = {},
        skip_local_visualization: bool = False,
    ) -> Result:
        """Generate a case and evaluate the code with the given input.

        Args:
            code (str): The code to evaluate.
            code_language (CodeLanguage | str): The code language.
            judge_version (JudgeVersion | str, optional): The judge version. Defaults to None.
            seed (list[int] | int, optional): The seed for the case generation. Defaults to 0.
            time_limit (float, optional): The time limit in seconds. Defaults to None.
            memory_limit (int | str, optional): The memory limit in bytes. Defaults to None.
            gen_kwargs (dict[str, Any]): The generation arguments. Defaults to an empty dictionary.
            skip_local_visualization (bool, optional): Whether to skip local visualization. Defaults to False.

        Returns:
            Result: The result of the evaluation.

        Raises:
            AleBenchError: If the session is finished or the resource usage is exceeded.
        """
        # Preprocessing (to avoid unnecessary computation, we check the resource usage of both functions here)
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        if not self._check_within_resource_usage_before(AleBenchFunction.CASE_GEN_EVAL):
            raise AleBenchError("The resource usage is exceeded.")
        seed, gen_kwargs = self._check_input_generation_arguments(seed=seed, gen_kwargs=gen_kwargs)
        (_, code, code_language, judge_version, time_limit, memory_limit) = self._check_run_cases_arguments(
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

        # Generation and evaluation (postprocessing is done in each function)
        input_str = self.case_gen(seed, **gen_kwargs)
        result = self.case_eval(
            input_str, code, code_language, judge_version, time_limit, memory_limit, skip_local_visualization
        )
        if not self._check_within_resource_usage_after(AleBenchFunction.CASE_GEN_EVAL):
            # NOTE: maybe this block is not reached because we check the resource usage in each function
            raise AleBenchError("The resource usage is exceeded after the action.")
        return result

    def local_visualization(
        self,
        input_str: list[str] | str,
        output_str: list[str] | str,
    ) -> list[Image.Image | None] | Image.Image | None:
        """Create local visualizations for the given input and output strings.

        Args:
            input_str (list[str] | str): The input string(s) for the visualization.
            output_str (list[str] | str): The output string(s) for the visualization.

        Returns:
            list[Image.Image | None] | Image.Image | None: The generated visualization(s).
                None if the problem has no local visualization or the visualization fails.
                Scalar value will be returned if `input_str` and `output_str` are scalar.
        """
        # Preprocessing
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        is_scalar = isinstance(input_str, str)
        input_str, output_str = self._check_local_visualization_arguments(input_str=input_str, output_str=output_str)

        # Local visualization
        local_visualization_images = local_visualization(
            inputs=input_str,
            outputs=output_str,
            problem_id=self._problem.metadata.problem_id,
            tool_dir=self._tool_dir,
            num_workers=self.num_workers,
        )

        # Postprocessing
        assert len(local_visualization_images) == len(input_str), (
            "The number of local visualization images must match the number of input strings."
        )

        # Save the action log and return the result
        self._action_log.append(
            json.dumps(
                {
                    "function": "local_visualization",
                    "arguments": {"input_str": input_str, "output_str": output_str},
                    "elapsed_time": elapsed_time,
                }
            )
        )

        return local_visualization_images[0] if is_scalar else local_visualization_images

    def public_eval(
        self,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        skip_local_visualization: bool = True,
    ) -> Result:
        """Evaluate the public score of the submission.

        Args:
            code (str): The code to evaluate.
            code_language (CodeLanguage | str): The code language.
            judge_version (JudgeVersion | str, optional): The judge version. Defaults to None.
            skip_local_visualization (bool, optional): Whether to skip local visualization. Defaults to True.

        Returns:
            Result: The result of the evaluation.

        Raises:
            AleBenchError: If the session is finished or the resource usage is exceeded.
            AssertionError: If the number of case results is not equal to the number of public seeds.
        """
        # Preprocessing
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        if not self._check_within_resource_usage_before(AleBenchFunction.PUBLIC_EVAL):
            raise AleBenchError("The resource usage is exceeded.")
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        _, code, code_language, judge_version, _, _ = self._check_run_cases_arguments(
            code=code, code_language=code_language, judge_version=judge_version
        )
        self._last_public_eval_time = dt.datetime.now(tz=dt.timezone.utc)

        # Evaluation
        public_case_results = run_cases(
            inputs=self._public_inputs,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=self._problem.constraints.time_limit,
            memory_limit=self._problem.constraints.memory_limit,
            problem_id=self._problem.metadata.problem_id,
            problem_type=self._problem.metadata.problem_type,
            tool_dir=self._tool_dir,
            return_details=True,
            skip_local_visualization=skip_local_visualization,
            num_workers=self.num_workers,
        )

        # Postprocessing
        assert len(public_case_results) == self.num_public_cases, (
            "The number of case results must be equal to the number of public seeds."
        )
        resource_usage = ResourceUsage(num_call_public_eval=1)
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.PUBLIC_EVAL):
            raise AleBenchError("The resource usage is exceeded after the action.")

        # Save the action log and return the result
        self._action_log.append(
            json.dumps(
                {
                    "function": "public_eval",
                    "arguments": {
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return Result(
            allow_score_non_ac=self.problem_id in ale_bench.constants.ALLOW_SCORE_NON_AC_PUBLIC,
            resource_usage=resource_usage,
            case_results=public_case_results,
        )

    def private_eval(
        self,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
    ) -> tuple[Result, int, int]:
        """Evaluate the private score of the submission.

        Args:
            code (str): The code to evaluate.
            code_language (CodeLanguage | str): The code language.
            judge_version (JudgeVersion | str, optional): The judge version. Defaults to None.

        Returns:
            Result: The result of the evaluation.
            int: The new rank of the submission.
            int: The new performance of the submission.

        Raises:
            AleBenchError: If the session is finished or the resource usage is exceeded.
            AssertionError: If the number of case results is not equal to the number of private seeds.
        """
        # Preprocessing
        try:
            if self.session_finished:
                raise AleBenchError("The session is finished.")
        except AleBenchError:
            raise AleBenchError("The session is finished.")
        if not self._check_within_resource_usage_before(AleBenchFunction.PRIVATE_EVAL):
            raise AleBenchError("The resource usage is exceeded.")
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        _, code, code_language, judge_version, _, _ = self._check_run_cases_arguments(
            code=code, code_language=code_language, judge_version=judge_version
        )
        self._last_private_eval_time = dt.datetime.now(tz=dt.timezone.utc)

        # Evaluation
        private_case_results = run_cases(
            inputs=self._private_inputs,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=self._problem.constraints.time_limit,
            memory_limit=self._problem.constraints.memory_limit,
            problem_id=self._problem.metadata.problem_id,
            problem_type=self._problem.metadata.problem_type,
            tool_dir=self._tool_dir,
            return_details=False,
            skip_local_visualization=True,
            num_workers=self.num_workers,
        )

        # Postprocessing
        assert len(private_case_results) == self.num_private_cases, (
            "The number of case results must be equal to the number of private seeds."
        )
        resource_usage = ResourceUsage(num_call_private_eval=1)
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.PRIVATE_EVAL):
            raise AleBenchError("The resource usage is exceeded after the action.")

        # Save the action log and return the result
        self._action_log.append(
            json.dumps(
                {
                    "function": "private_eval",
                    "arguments": {
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        private_result = Result(
            allow_score_non_ac=self.problem_id in ale_bench.constants.ALLOW_SCORE_NON_AC_PRIVATE,
            resource_usage=resource_usage,
            case_results=private_case_results,
        )
        new_rank, new_performance_rank, relative_scores = self._standings.get_new_rank(private_result)
        new_performance = self._rank_performance_map.get_performance(new_performance_rank)
        processed_relative_cases = [
            CaseResult(
                input_str=None,
                output_str=None,
                error_str=None,
                judge_result=case_result.judge_result,
                message="",
                absolute_score=case_result.absolute_score,
                relative_score=relative_score,
                local_visualization=None,
                execution_time=case_result.execution_time,
                memory_usage=case_result.memory_usage,
            )
            for relative_score, case_result in zip(relative_scores, private_result.case_results)
        ]  # NOTE: `input_str`, `output_str`, `error_str`, `message` and `local_visualization` will not be provided
        processed_private_result = Result(
            allow_score_non_ac=private_result.allow_score_non_ac,
            resource_usage=private_result.resource_usage,
            case_results=processed_relative_cases,
        )
        return processed_private_result, new_rank, new_performance

    def save(self, filepath: str | os.PathLike[str] = "session.json") -> None:
        """Save the session to a JSON file.

        You can restart the session from this file by using the `load` method.

        Args:
            filepath (str | os.PathLike[str], optional): The path to save the session. Defaults to "session.json".
        """
        filepath_path = Path(filepath)
        with open(filepath_path, "w") as f:
            json.dump(
                {
                    "problem_id": self._problem.metadata.problem_id,
                    "lite_version": self._lite_version,
                    "public_seeds": self._public_seeds,
                    "private_seeds": self._private_seeds,
                    "use_same_time_scale": self._use_same_time_scale,
                    "maximum_resource_usage": self._maximum_resource_usage.model_dump(),
                    "session_duration": self._session_duration.total_seconds(),
                    "visualization_server_port": self._visualization_server_port,
                    "num_workers": self.num_workers,
                    "current_resource_usage": self._current_resource_usage.model_dump(),
                    "action_log": self._action_log,
                    "last_public_eval_time": self._last_public_eval_time.timestamp(),
                    "last_private_eval_time": self._last_private_eval_time.timestamp(),
                    "session_started_at": self._session_started_at.timestamp(),
                    "session_paused_at": dt.datetime.now(tz=dt.timezone.utc).timestamp(),
                },
                f,
                ensure_ascii=False,
            )
        print(f"Session saved to {filepath_path.resolve()}")

    def close(self) -> None:
        """Close the session and clean up resources."""
        shutil.rmtree(self._tool_dir, ignore_errors=True)
        if self._visualization_server_container_id is not None:
            print("Stopping the visualization server...")
            with docker_client() as client:
                visualization_server_container = client.containers.get(self._visualization_server_container_id)
                visualization_server_container.stop()
                visualization_server_container.remove(force=True)
            print("Visualization server stopped.")
            self._run_visualization_server = False
            self._visualization_server_port = None
            self._visualization_server_container_id = None

    # Properties
    @property
    def problem(self) -> Problem:
        """Get the problem object.

        Returns:
            Problem: The problem object.
        """
        return self._problem

    @property
    def problem_id(self) -> str:
        """Get the problem ID.

        Returns:
            str: The problem ID.
        """
        return self._problem.metadata.problem_id

    @property
    def lite_version(self) -> bool:
        """Get whether the session is in lite version.

        Returns:
            bool: Whether the session is in lite version.
        """
        return self._lite_version

    @property
    def public_seeds(self) -> list[int]:
        """Get the public seeds.

        Returns:
            list[int]: The public seeds.
        """
        return self._public_seeds

    @property
    def num_public_cases(self) -> int:
        """Get the number of public cases.

        Returns:
            int: The number of public cases.
        """
        return len(self._public_seeds)

    @property
    def private_seeds(self) -> NoReturn:
        """Get the private seeds.

        Raises:
            AleBenchError: Accessing private seeds is not allowed.
        """
        raise AleBenchError("Accessing private seeds is not allowed.")

    @property
    def num_private_cases(self) -> int:
        """Get the number of private cases.

        Returns:
            int: The number of private cases.
        """
        return len(self._private_seeds)

    @property
    def standings(self) -> NoReturn:
        """Get the standings.

        Raises:
            AleBenchError: Accessing standings is not allowed.
        """
        raise AleBenchError("Accessing standings is not allowed.")

    @property
    def rank_performance_map(self) -> NoReturn:
        """Get the rank performance map.

        Raises:
            AleBenchError: Accessing rank performance map is not allowed.
        """
        raise AleBenchError("Accessing rank performance map is not allowed.")

    @property
    def tool_dir(self) -> Path:
        """Get the directory for the tools.

        Returns:
            Path: The directory for the tools.
        """
        return self._tool_dir

    @property
    def rust_src_dir(self) -> Path:
        """Get the directory for the Rust tools source code.

        Returns:
            Path: The directory for the tools.
        """
        return self._tool_dir / "tools" / "src"

    @property
    def use_same_time_scale(self) -> bool:
        """Get whether to use the same time scale.

        Returns:
            bool: Whether to use the same time scale.
        """
        return self._use_same_time_scale

    @property
    def maximum_resource_usage(self) -> ResourceUsage:
        """Get the maximum resource usage.

        Returns:
            ResourceUsage: The maximum resource usage.
        """
        return self._maximum_resource_usage

    @property
    def current_resource_usage(self) -> ResourceUsage:
        """Get the current resource usage.

        Returns:
            ResourceUsage: The current resource usage.
        """
        return self._current_resource_usage

    @property
    def remaining_resource_usage(self) -> ResourceUsage:
        """Get the remaining resource usage.

        Returns:
            ResourceUsage: The remaining resource usage.
        """
        return self._maximum_resource_usage - self._current_resource_usage

    @property
    def action_log(self) -> list[str]:
        """Get the action log.

        Returns:
            list[str]: The action log.
        """
        return self._action_log

    @property
    def last_public_eval_time(self) -> dt.datetime:
        """Get the time when the last public evaluation was performed.

        Returns:
            dt.datetime: The time when the last public evaluation was performed.
        """
        return self._last_public_eval_time

    @property
    def next_public_eval_time(self) -> dt.datetime:
        """Get the time when the next public evaluation can be performed.

        Returns:
            dt.datetime: The time when the next public evaluation can be performed.
        """
        if self._use_same_time_scale:
            return self._last_public_eval_time + dt.timedelta(
                seconds=self._problem.metadata.submission_interval_seconds
            )
        else:
            return self._last_public_eval_time

    @property
    def last_private_eval_time(self) -> dt.datetime:
        """Get the time when the last private evaluation was performed.

        Returns:
            dt.datetime: The time when the last private evaluation was performed.
        """
        return self._last_private_eval_time

    @property
    def session_duration(self) -> dt.timedelta:
        """Get the duration of the session.

        Returns:
            dt.timedelta: The duration of the session.
        """
        return self._session_duration

    @property
    def session_started_at(self) -> dt.datetime:
        """Get the time when the session started.

        Returns:
            dt.datetime: The time when the session started.
        """
        return self._session_started_at

    @property
    def session_remaining_time(self) -> dt.timedelta:
        """Get the remaining time of the session.

        Returns:
            dt.timedelta: The remaining time of the session.
        """
        return self._session_started_at + self._session_duration - dt.datetime.now(tz=dt.timezone.utc)

    @property
    def session_finished(self) -> bool:
        """Check if the session is finished.

        Returns:
            bool: Whether the session is finished.

        Raises:
            AleBenchError: If the session is finished.
        """
        is_finished = not self._check_within_resource_usage_before(AleBenchFunction.PRIVATE_EVAL)
        return is_finished

    @property
    def run_visualization_server(self) -> bool:
        """Get whether to run the visualization server.

        Returns:
            bool: Whether to run the visualization server.
        """
        return self._run_visualization_server

    @property
    def visualization_server_port(self) -> int | None:
        """Get the port number of the visualization server.

        Returns:
            int | None: The port number of the visualization server or None if not running.
        """
        return self._visualization_server_port

    # Checkers
    def _check_within_resource_usage_before(self, function_type: AleBenchFunction) -> bool:
        """Check if the current resource usage is within the maximum resource usage before the action is performed."""
        if self.session_remaining_time.total_seconds() <= 0:
            # NOTE: You have to call `private_eval` to submit your solution
            # This is slightly different from the original competition
            # However, this is not critical because anyway user can't submit after the session is finished
            raise AleBenchError("The session has already finished.")
        is_within_resource_usage = all(
            [
                getattr(self._current_resource_usage, field) < getattr(self._maximum_resource_usage, field)
                for field in CHECK_RESOURCE_USAGE_FIELDS[function_type]
            ]
        )
        if not is_within_resource_usage:
            raise AleBenchError(f"Exceeded the maximum resource usage for the `{function_type.value}` function.")
        if self._use_same_time_scale and function_type == AleBenchFunction.PUBLIC_EVAL:
            if dt.datetime.now(tz=dt.timezone.utc) < self.next_public_eval_time:
                raise AleBenchError("The next public evaluation is not allowed yet.")
        return is_within_resource_usage

    def _check_within_resource_usage_after(self, function_type: AleBenchFunction) -> bool:
        """Check if the current resource usage is within the maximum resource usage after the action is performed."""
        is_within_resource_usage = all(
            [
                getattr(self._current_resource_usage, field) <= getattr(self._maximum_resource_usage, field)
                for field in CHECK_RESOURCE_USAGE_FIELDS[function_type]
            ]
        )  # NOTE: `<=` is used to allow the last action
        if not is_within_resource_usage:
            raise AleBenchError(
                f"Exceeded the maximum resource usage for the `{function_type.value}` function after the action."
            )
        return is_within_resource_usage

    def _check_input_generation_arguments(
        self,
        seed: list[int] | int | None = None,
        gen_kwargs: dict[str, Any] | None = None,
    ) -> tuple[list[int], dict[str, Any]]:
        """Check if the arguments for `generate_inputs` are valid."""
        # Check `seed`
        if seed is None:
            seed = [0]
        else:
            if isinstance(seed, int):
                seed = [seed]
            for s in seed:
                if s < 0 or s > 18446744073709551615:  # NOTE: Unsigned 64-bit integer
                    raise AleBenchError("`seed` must be between 0 and 2^64 - 1.")

        # Check `gen_kwargs`
        ret_gen_kwargs = {}
        if gen_kwargs is not None:
            for key in gen_kwargs.keys():
                if key == "dir":
                    warnings.warn("`dir` is a reserved keyword and will be ignored.")
                else:
                    ret_gen_kwargs[key] = gen_kwargs[key]

        return seed, ret_gen_kwargs

    def _check_local_visualization_arguments(
        self,
        input_str: list[str] | str,
        output_str: list[str] | str,
    ) -> tuple[list[str], list[str]]:
        """Check if the arguments for `local_visualization` are valid."""
        if isinstance(input_str, str) and isinstance(output_str, str):
            input_str = [input_str]
            output_str = [output_str]
        elif isinstance(input_str, str) or isinstance(output_str, str):
            raise AleBenchError("Both `input_str` and `output_str` must be either a string or a list of strings.")
        # Check the length of `input_str` and `output_str`
        if len(input_str) != len(output_str):
            raise AleBenchError("The number of input strings and output strings must be the same.")
        # Check if the input and output strings are empty
        if len(input_str) == 0 or any(in_s.strip() == "" for in_s in input_str):
            raise AleBenchError("The input string is empty.")
        if len(output_str) == 0 or any(out_s.strip() == "" for out_s in output_str):
            raise AleBenchError("The output string is empty.")
        return input_str, output_str

    def _check_run_cases_arguments(
        self,
        input_str: list[str] | str | None = None,
        allow_empty_input: bool = False,
        code: str | None = None,
        code_language: CodeLanguage | str | None = None,
        judge_version: JudgeVersion | str | None = None,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
    ) -> tuple[list[str], str, CodeLanguage, JudgeVersion, float, int]:
        """Check if the arguments for `run_cases` are valid."""
        # Check `input_str`
        if input_str is None:
            input_str = [""]
        else:
            if isinstance(input_str, str):
                input_str = [input_str]
            for in_s in input_str:
                if in_s.strip() == "" and not allow_empty_input:
                    raise AleBenchError("The input string is empty.")

        # Check `code`
        if code is None:
            raise AleBenchError("`code` must be specified.")
        else:
            code_byte_size = len(code.encode("utf-8"))
            if code_byte_size > 524288:  # NOTE: 512 KiB
                raise AleBenchError("The size of the submission code exceeds the limit (512 KiB).")
            if code.strip() == "":
                raise AleBenchError("The submission code is empty.")

        # Check `code_language` and `judge_version`
        if code_language is None:
            raise AleBenchError("`code_language` must be specified.")
        else:
            if isinstance(code_language, str):
                try:
                    code_language = CodeLanguage(code_language)
                except ValueError:
                    raise AleBenchError(
                        f"Invalid code language. Available options: {', '.join(CodeLanguage.__members__)}"
                    )
            if judge_version is None:
                judge_version = JudgeVersion.V202301  # NOTE: Use the judge version 202301 by default
            else:
                if isinstance(judge_version, str):
                    try:
                        judge_version = JudgeVersion(judge_version)
                    except ValueError:
                        raise AleBenchError(
                            f"Invalid judge version. Available options: {', '.join(JudgeVersion.__members__)}"
                        )
            if judge_version == JudgeVersion.V201907 and (
                code_language == CodeLanguage.CPP20 or code_language == CodeLanguage.CPP23
            ):
                raise AleBenchError("The judge version 201907 does not support C++20 or C++23.")

        # Check `time_limit`
        if time_limit is None:
            time_limit = self._problem.constraints.time_limit  # NOTE: Use the default time limit
        if time_limit <= 0.0:
            raise AleBenchError("`time_limit` must be positive.")

        # Check `memory_limit`
        if memory_limit is None:
            memory_limit = self._problem.constraints.memory_limit  # NOTE: Use the default memory limit
        else:
            if isinstance(memory_limit, str):
                memory_limit = memory_limit.lower()
                try:
                    if memory_limit.endswith("b"):
                        memory_limit = int(memory_limit[:-1])
                    elif memory_limit.endswith("k"):
                        memory_limit = int(memory_limit[:-1]) * 1024
                    elif memory_limit.endswith("m"):
                        memory_limit = int(memory_limit[:-1]) * 1048576
                    elif memory_limit.endswith("g"):
                        memory_limit = int(memory_limit[:-1]) * 1073741824
                    else:
                        memory_limit = int(memory_limit)
                except ValueError:
                    raise AleBenchError("Invalid `memory_limit` format. Use 'b', 'k', 'm', or 'g' suffixes.")
            memory_limit = min(memory_limit, ale_bench.constants.MAX_MEMORY_LIMIT)
            if memory_limit < 6291456:
                raise AleBenchError("`memory_limit` must be greater than or equal to 6MB.")

        return input_str, code, code_language, judge_version, time_limit, memory_limit
