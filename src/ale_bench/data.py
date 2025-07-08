from __future__ import annotations

import datetime as dt
import json
import math
import os
import shutil
import tempfile
import zipfile
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any

import docker
import polars as pl
from PIL import Image
from docker.models.containers import Container as DockerContainer
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

import ale_bench.constants
from ale_bench.result import JudgeResult, Result
from ale_bench.utils import get_cache_dir, get_local_data_dir, read_svg


class ProblemType(str, Enum):
    """Problem types for ALE-Bench.

    - `batch`: Batch problem
    - `reactive`: Reactive problem
    """

    BATCH = "batch"
    REACTIVE = "reactive"


class ScoreType(str, Enum):
    """Score types for ALE-Bench.

    - `minimize`: Minimize the absolute score
    - `maximize`: Maximize the absolute score
    """

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class RankPerformanceMap(BaseModel):
    """The map of rank to performance.

    We assume that approximations of performance by linear interpolation do not deviate significantly because:
    - no ties occur in the top tier of the standings
    - AI will not perform near zero score (we don't know the exact number of score 0 participants)
    """

    model_config = ConfigDict(frozen=True)

    raw_data: list[tuple[int, int]] = Field(
        description="Raw data of the map of rank to performance (rank, performance)"
    )
    data: dict[float, int] = Field(default_factory=dict, description="Map of rank to performance")

    @field_validator("raw_data")
    @classmethod
    def validate_raw_data(cls, raw_data: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Validate the raw data."""
        if len(raw_data) <= 1:
            raise ValueError("The raw data must contain at least 2 entries.")
        for i in range(1, len(raw_data)):
            if raw_data[i - 1][0] > raw_data[i][0]:
                raise ValueError("The rank must be sorted in ascending order.")
            if raw_data[i - 1][1] < raw_data[i][1]:
                raise ValueError("The performance must be sorted in descending order.")
        return raw_data

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization method."""
        # Create a map of rank to performance
        self.data.clear()  # NOTE: Ensure the map is empty before populating it
        for i in range(len(self.raw_data) - 1):
            rank, performance = self.raw_data[i]
            next_rank, next_performance = self.raw_data[i + 1]
            if rank == next_rank:
                assert performance == next_performance, "Something went wrong: `performance` != `next_performance`."
                continue  # NOTE: tie
            actual_rank = float((rank + next_rank - 1) / 2)  # NOTE: Use the average of the rank range for performance
            self.data[actual_rank] = performance
        self.data[float(self.raw_data[-1][0])] = self.raw_data[-1][1]  # NOTE: Add the last score 0 entry

    def get_performance(self, rank: int | float) -> int:
        """Get the performance for a given rank.

        Actual performance is calculated as written in https://img.atcoder.jp/file/AHC_rating_v2_en.pdf
        The performance will be the same if the rank is the same
        If new rank is in the standings, return the same performance
        Otherwise, return the linear interpolated performance between the previous and the next entries
        Because sometimes the ties happen, so we sometimes can't get the exact performance from the standings
        We approximate the new performance as the actual performance is calculated by the complicated formula
        In addition the real performance should be calculated with entire re-ranked standings with internal information

        Args:
            rank (int | float): The rank to get the performance for.

        Returns:
            int: The (approximated) performance for the given rank.
        """
        rank = float(rank)
        if rank in self.data:
            return self.data[rank]
        # NOTE: linear interpolation with the previous and the next entries
        sorted_keys = sorted(list(self.data.keys()))
        lose, win = -1, len(sorted_keys)
        while win - lose > 1:
            mid = (lose + win) // 2
            if rank < sorted_keys[mid]:
                win = mid
            else:
                lose = mid
        if win == len(sorted_keys):
            assert False, "Something went wrong: `win` should be less than `len(sorted_keys)`."
        if win == 0:
            win = 1  # NOTE: to avoid index out of range and use the 1st & 2nd entries
        rank_high = sorted_keys[win - 1]
        rank_low = sorted_keys[win]
        perf_high = self.data[rank_high]
        perf_low = self.data[rank_low]
        return round(perf_high - (perf_high - perf_low) * (rank - rank_high) / (rank_low - rank_high))


class RelativeScoreType(str, Enum):
    """Relative score types for ALE-Bench.

    - `min`: Relative score is calculated by the absolute score, lower absolute score is better
    - `max`: Relative score is calculated by the absolute score, higher absolute score is better
    - `rank_min`: Relative score is calculated by the rank, lower absolute score is better
    - `rank_max`: Relative score is calculated by the rank, higher absolute score is better
    """

    MIN = "min"
    MAX = "max"
    RANK_MIN = "rank_min"
    RANK_MAX = "rank_max"


class RelativeResults(BaseModel):
    """Relative results of a problem in ALE-Bench.

    We assume that the absolute scores must be positive when `relative_score` type is `min` or `rank_min`.
    """

    model_config = ConfigDict(frozen=True)

    absolute_scores: list[list[int]] = Field(
        description="Relative results data. List of cases (each case is a list of scores)",
    )
    relative_score_type: RelativeScoreType = Field(
        description="Relative score type of the problem (min, max, rank_min, rank_max)",
    )
    relative_max_score: int = Field(description="Maximum score per case for the relative score")

    @field_validator("absolute_scores")
    @classmethod
    def validate_absolute_scores(cls, absolute_scores: list[list[int]]) -> list[list[int]]:
        """Validate the absolute_scores."""
        if len(absolute_scores) == 0:
            raise ValueError("The relative results absolute_scores cannot be empty.")
        num_participants = len(absolute_scores[0])
        if num_participants == 0:
            raise ValueError("The number of participants must be greater than 0.")
        for i in range(len(absolute_scores)):
            if len(absolute_scores[i]) != num_participants:
                raise ValueError("The number of participants must be the same for all cases.")
        return absolute_scores

    def recalculate_relative_score(self, new_scores: list[int]) -> tuple[int, list[int], list[int]]:
        """Recalculate the relative score with additional absolute scores.

        Args:
            new_scores (list[int]): New absolute scores for each case.
                Note that not accepted case should be -1, and accepted case with score 0 should be 0.

        Returns:
            tuple[int, list[int], list[int]]: Tuple of the new overall relative score, new relative scores for each case
                and the list of recalculated overall relative scores.
                The first element is the new overall relative score of the additional absolute scores.
                The second element is relative scores of new scores for each case.
                The third element is the list of recalculated overall relative scores of each user (descending order).
                    This includes the additional absolute scores and can be used for calculating the new rank.
        """
        if len(new_scores) != len(self.absolute_scores):
            raise ValueError(
                f"The number of new scores ({len(new_scores)}) must be "
                f"the same as the number of cases ({len(self.absolute_scores)})."
            )
        new_relative_case_scores = []
        new_overall_relative_scores_existing = [0 for _ in range(len(self.absolute_scores[0]))]
        for new_score, existing_scores in zip(new_scores, self.absolute_scores):
            # Collect the new score and existing scores for the case
            case_scores = deepcopy(existing_scores)
            if new_score < 0:  # NOTE: Rejected case
                case_scores.append(-1)
            elif new_score == 0:  # NOTE: Accepted case with score 0
                assert self.relative_score_type not in {RelativeScoreType.MIN}, (
                    "If `relative_score_type` is `min`, absolute score should be greater than 0."
                )
                case_scores.append(0)
            else:
                case_scores.append(new_score)
            # Calculate the new relative score
            sorted_case_scores = sorted([case_score for case_score in case_scores if case_score >= 0])
            for user_idx, user_score in enumerate(case_scores):
                relative_score = 0
                if self.relative_score_type == RelativeScoreType.MAX:
                    if user_score >= 0:
                        relative_score = self.relative_max_score * user_score // sorted_case_scores[-1]
                        if self.relative_max_score * user_score % sorted_case_scores[-1] * 2 >= sorted_case_scores[-1]:
                            relative_score += 1  # Round up
                elif self.relative_score_type == RelativeScoreType.MIN:
                    if user_score == 0:
                        raise ValueError(
                            f"Zero score is not allowed for `relative_score_type` {self.relative_score_type}."
                        )
                    elif user_score > 0:
                        relative_score = self.relative_max_score * sorted_case_scores[0] // user_score
                        if self.relative_max_score * sorted_case_scores[0] % user_score * 2 >= user_score:
                            relative_score += 1  # Round up
                elif user_score >= 0:  # NOTE: RANK_MIN or RANK_MAX
                    n_submit, n_lose, n_tie = (
                        len(case_scores),
                        0,
                        -1,
                    )  # NOTE: Exclude the user score itself from the tie count
                    for abs_score in sorted_case_scores:
                        if user_score == abs_score:
                            n_tie += 1
                        elif user_score < abs_score and self.relative_score_type == RelativeScoreType.RANK_MAX:
                            n_lose += 1
                        elif user_score > abs_score and self.relative_score_type == RelativeScoreType.RANK_MIN:
                            n_lose += 1
                    relative_score = round(self.relative_max_score * (1.0 - (n_lose + n_tie / 2) / n_submit))
                # Add the relative score to the new overall relative score
                # NOTE: The additional user score is always the last one in the list
                if user_idx == len(existing_scores):
                    new_relative_case_scores.append(relative_score)
                else:
                    new_overall_relative_scores_existing[user_idx] += relative_score
        # Calculate the new overall relative scores for all users
        new_overall_relative_score = sum(new_relative_case_scores)
        new_overall_relative_scores = sorted(
            new_overall_relative_scores_existing + [new_overall_relative_score], reverse=True
        )
        return new_overall_relative_score, new_relative_case_scores, new_overall_relative_scores


class Standings(BaseModel):
    """Standings of a problem in ALE-Bench.

    We assume that there are people with score 0 in the standings.
    """

    model_config = ConfigDict(frozen=True)

    standings_scores: list[tuple[int, int]] = Field(description="List of standings scores (rank, score)")
    score_rank_list: list[tuple[int, int, int]] = Field(
        default_factory=list, description="List of score to rank (score, start rank, end rank)"
    )
    relative_results: RelativeResults | None = Field(
        default=None, description="Result (absolute score) of the private cases"
    )

    @field_validator("standings_scores")
    @classmethod
    def validate_data(cls, standings_scores: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Validate the standings data."""
        if len(standings_scores) == 0:
            raise ValueError("The standings scores cannot be empty.")
        for i in range(1, len(standings_scores)):
            if standings_scores[i - 1][0] > standings_scores[i][0]:
                raise ValueError("The rank must be sorted in ascending order.")
            if standings_scores[i - 1][1] < standings_scores[i][1]:
                raise ValueError("The score must be sorted in descending order.")
            if standings_scores[i - 1][1] <= 0:
                raise ValueError("The score must be greater than 0 except for the last entry.")
        if standings_scores[-1][1] != 0:
            raise ValueError("The last entry must be an entry with score 0.")
        return standings_scores

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization method."""
        self.score_rank_list.clear()  # NOTE: Ensure the map is empty before populating it
        rank_start = self.standings_scores[0][0]
        for i in range(1, len(self.standings_scores)):
            score = self.standings_scores[i - 1][1]
            next_rank, next_score = self.standings_scores[i]
            if score == next_score:
                continue  # NOTE: In early contests, the same score may have different ranks
            self.score_rank_list.append((score, rank_start, next_rank - 1))
            rank_start = next_rank
        self.score_rank_list.append(
            (self.standings_scores[-1][1], self.standings_scores[-1][0], self.standings_scores[-1][0])
        )  # Add the last score 0 entry
        for i in range(len(self.score_rank_list) - 1):
            _, _, end_rank = self.score_rank_list[i]
            _, next_start_rank, _ = self.score_rank_list[i + 1]
            assert next_start_rank == end_rank + 1, "Something went wrong: `next_start_rank` != `end_rank + 1`."

    def get_new_rank(self, private_result: Result) -> tuple[int, float, list[int]]:
        """Get the new rank for a given private result.

        Args:
            private_result (Result): The private result to get the new rank for.

        Returns:
            tuple[int, float, list[int]]: The tuple of the new rank in the standings, the new rank
                for the performance calculation, and the list of relative scores.
                The first element is the new rank for the given private result (in the standings).
                The second element is the new rank for the given private result (to calculate the performance).
                If the new score has ties, the rank will be the average of the ranks.
                The third element is the list of relative scores for each case.

        Raises:
            ValueError: If the score is negative.
        """
        if self.relative_results is not None:  # NOTE: Need to recalculate the relative score
            new_absolute_scores = [
                case_result.absolute_score if case_result.judge_result == JudgeResult.ACCEPTED else -1
                for case_result in private_result.case_results
            ]
            (new_relative_score, new_relative_case_scores, new_relative_scores) = (
                self.relative_results.recalculate_relative_score(new_absolute_scores)
            )
            if new_relative_score == 0:  # NOTE: The lowest score
                return (
                    self.score_rank_list[-1][1],
                    float(self.score_rank_list[-1][1]),
                    new_relative_case_scores,
                )  # NOTE: The last entry is the lowest score (with score 0)
            new_rank, performance_additional = 1, 0.0
            for score in new_relative_scores:
                if new_relative_score > score:
                    break
                elif new_relative_score == score:
                    performance_additional += 0.5
                else:
                    new_rank += 1
            # NOTE: We need to subtract 1.0 from the performance_additional.
            # 0.5 for `new_relative_score` and 0.5 for the actual user's score in the standing
            # because we don't recalculate the performance and use the existing rank performance map
            return new_rank, float(new_rank) + max(performance_additional - 1.0, 0.0), new_relative_case_scores
        # NOTE: The relative score is not used and absolute score is used for the standings
        # NOTE: `overall_absolute_score` is already processed whether the overall judge is ACCEPTED or not
        new_score = private_result.overall_absolute_score
        new_case_scores = [
            case_result.absolute_score if case_result.judge_result == JudgeResult.ACCEPTED else 0
            for case_result in private_result.case_results
        ]
        if new_score == 0:  # NOTE: The lowest score
            return (
                self.score_rank_list[-1][1],
                float(self.score_rank_list[-1][1]),
                new_case_scores,
            )  # NOTE: The last entry is the lowest score (with score 0)
        for score, start_rank, end_rank in self.score_rank_list:
            if new_score > score:
                return start_rank, float(start_rank), new_case_scores
            elif new_score == score:
                return start_rank, float((start_rank + end_rank) / 2), new_case_scores  # NOTE: Average of the ranks
        assert False, "Something went wrong in `get_new_rank` method."


class ProblemMetaData(BaseModel):
    """Metadata of a problem in ALE-Bench."""

    model_config = ConfigDict(frozen=True)

    problem_id: str = Field(description="Problem ID")
    start_at: dt.datetime = Field(description="Start time of the problem in ISO 8601 format")
    end_at: dt.datetime = Field(description="End time of the problem in ISO 8601 format")
    contest_url: str = Field(description="URL of the original contest")
    title: str = Field(description="Title of the problem")
    problem_type: ProblemType = Field(description="Problem type of the problem")
    score_type: ScoreType = Field(description="Score type of the problem")

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization method."""
        if self.start_at >= self.end_at:
            raise ValueError("The start time must be earlier than the end time.")

    @field_serializer("start_at")
    def serialize_start_at(self, start_at: dt.datetime) -> str:
        """Serialize start_at to ISO 8601 format."""
        return start_at.isoformat()

    @field_serializer("end_at")
    def serialize_end_at(self, end_at: dt.datetime) -> str:
        """Serialize end_at to ISO 8601 format."""
        return end_at.isoformat()

    @property
    def duration(self) -> dt.timedelta:
        """Duration of the problem.

        Returns:
            dt.timedelta: Duration of the problem.
        """
        return self.end_at - self.start_at

    @property
    def submission_interval_seconds(self) -> int:
        """Submission interval in seconds.

        Returns:
            int: Submission interval in seconds.
        """
        if self.duration < dt.timedelta(days=1):
            return 300  # NOTE: 5 minutes for short contests
        else:
            return 1800  # NOTE: 30 minutes for long contests


class ProblemConstraints(BaseModel):
    """Constraints of a problem in ALE-Bench."""

    model_config = ConfigDict(frozen=True)

    time_limit: float = Field(description="Time limit of the problem in seconds")
    memory_limit: int = Field(description="Memory limit of the problem in bytes")


class Problem(BaseModel):
    """Problem class for ALE-Bench."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    metadata: ProblemMetaData
    constraints: ProblemConstraints = Field(description="Problem constraints")
    statement: str = Field(description="Problem statement (English) in Markdown format")
    statement_ja: str = Field(description="Problem statement (Japanese) in Markdown format")
    statement_images: dict[str, Image.Image | list[Image.Image]] = Field(
        description="Problem statement images in PIL Image format (key: image name, value: image object)",
        default_factory=dict,
    )
    example_input: str = Field(description="Example input")
    example_output: str = Field(description="Example output")
    tool_readme: str = Field(description="Readme of the tools in Markdown format")

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization method."""
        for image_name in self.statement_images.keys():
            if image_name not in self.statement:
                raise ValueError(f"Image `{image_name}` not found in the problem statement.")


class Seeds(BaseModel):
    """Seed class for ALE-Bench."""

    model_config = ConfigDict(frozen=True)

    public: list[int] = Field(description="Public seed values")
    private: list[int] = Field(description="Private seed values")


def list_problem_ids(lite_version: bool = False) -> list[str]:
    """Get the problem IDs available in the Hugging Face Hub.

    Args:
        lite_version (bool): Whether to list the lite version of problem IDs. Defaults to False.

    Returns:
        list[str]: A set of problem IDs.
    """
    local_data_dir = get_local_data_dir()
    filename = "problem_ids_lite.txt" if lite_version else "problem_ids.txt"
    if local_data_dir is None or not (local_data_dir / filename).is_file():
        cache_dir = get_cache_dir()
        problem_ids_file_path = hf_hub_download(
            repo_id=ale_bench.constants.HUGGING_FACE_REPO,
            filename=filename,
            repo_type="dataset",
            cache_dir=cache_dir,
        )
    else:
        problem_ids_file_path = str(local_data_dir / filename)
    with open(problem_ids_file_path, "r") as f:
        problem_ids = f.read().splitlines()
    return problem_ids


def load_problem(problem_id: str, lite_version: bool) -> tuple[Problem, Seeds, Standings, RankPerformanceMap, Path]:
    """Load a problem from the Hugging Face Hub.

    Args:
        problem_id (str): The ID of the problem to load.
        lite_version (bool): Whether to use the lite version of seeds.

    Returns:
        tuple[Problem, Seeds, Standings, RankPerformanceMap, Path]: A tuple containing
        the problem object, seeds object, standings object, rank performance map object, and the data root path.
    """
    cache_dir = get_cache_dir()
    local_data_dir = get_local_data_dir()
    if local_data_dir is None or not (local_data_dir / f"{problem_id}.zip").is_file():
        # Load the problem data from the Hugging Face Hub
        data_path = hf_hub_download(
            repo_id=ale_bench.constants.HUGGING_FACE_REPO,
            filename=f"{problem_id}.zip",
            repo_type="dataset",
            cache_dir=cache_dir,
        )
    else:
        data_path = str(local_data_dir / f"{problem_id}.zip")

    # Create the temporary directory and extract the problem zip data
    data_root = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(data_path, "r") as zf:
        zf.extractall(data_root)
    shutil.copytree(data_root / problem_id, data_root, copy_function=shutil.move, dirs_exist_ok=True)
    shutil.rmtree(data_root / problem_id)  # Remove the original directory after moving

    # Load the problem data
    data = json.load((data_root / "data.json").open("r"))
    (data_root / "data.json").unlink()  # Remove the JSON file after loading
    metadata = data["metadata"]
    assert metadata["problem_id"] == problem_id, f"Problem ID mismatch: {metadata['problem_id']} != {problem_id}"
    constraints = ProblemConstraints(**data["constraints"])
    image_files = data["image_files"]
    seeds = Seeds(
        public=data["seeds"]["public_lite"] if lite_version else data["seeds"]["public"],
        private=data["seeds"]["private_lite"] if lite_version else data["seeds"]["private"],
    )

    # Load the problem statement
    statement_en = (data_root / "statement_en.md").read_text()
    (data_root / "statement_en.md").unlink()  # Remove the English statement file after loading
    statement_ja = (data_root / "statement_ja.md").read_text()
    (data_root / "statement_ja.md").unlink()  # Remove the Japanese statement file after loading
    example_input = (data_root / "example_input.txt").read_text()
    (data_root / "example_input.txt").unlink()  # Remove the example input file after loading
    example_output = (data_root / "example_output.txt").read_text()
    (data_root / "example_output.txt").unlink()  # Remove the example output file after loading

    # Load the standings score data
    df_standings_score = pl.read_csv(
        data_root / "standings_scores_lite.csv" if lite_version else data_root / "standings_scores.csv"
    )
    (data_root / "standings_scores.csv").unlink()  # Remove the standings score file after loading
    (data_root / "standings_scores_lite.csv").unlink()  # Remove the standings score file after loading
    standings_score_data = df_standings_score.sort(by=["rank"], descending=[False]).rows()

    # Load the relative submission results
    relative_results = None
    if "relative_score_type" in metadata:
        assert "relative_max_score" in metadata, "relative_max_score is required for relative results"
        assert (data_root / "relative_results.csv").is_file(), "relative_results.csv is required for relative results"
        assert (data_root / "relative_results_lite.csv").is_file(), (
            "relative_results_lite.csv is required for relative results"
        )
        df_relative_results = pl.read_csv(
            data_root / "relative_results_lite.csv" if lite_version else data_root / "relative_results.csv"
        )
        (data_root / "relative_results.csv").unlink()  # Remove the relative results file after loading
        (data_root / "relative_results_lite.csv").unlink()  # Remove the relative results file after loading

        assert df_relative_results.columns == [f"private_{i}" for i in range(len(seeds.private))], (
            "The columns of relative_results.csv must be private_0, private_1, ..."
        )
        relative_results = RelativeResults(
            absolute_scores=[df_relative_results[col].to_list() for col in df_relative_results.columns],
            relative_score_type=metadata["relative_score_type"],
            relative_max_score=metadata["relative_max_score"],
        )
        assert len(relative_results.absolute_scores) == len(seeds.private), "Number of private cases mismatch"
    standings = Standings(standings_scores=standings_score_data, relative_results=relative_results)

    # Load the performance data
    df_performance = pl.read_csv(data_root / "performance.csv")
    (data_root / "performance.csv").unlink()  # Remove the performance file after loading
    performance_data = df_performance.sort(by=["rank"], descending=[False]).rows()
    rank_performance_map = RankPerformanceMap(raw_data=performance_data)

    # Load the problem statement images
    statement_images: dict[str, Image.Image | list[Image.Image]] = {}
    for filename, frames in image_files.items():
        images: list[Image.Image] = []
        for frame in frames:
            if frame.endswith(".svg"):
                # NOTE: SVG images are not supported by PIL, so we use a custom function to read them.
                # NOTE: Default image size is 1000 x 1000
                images.append(read_svg((data_root / "images" / frame).read_text()))
            else:
                images.append(Image.open(data_root / "images" / frame))
        # NOTE: If there are multiple images, we consider them as a video
        statement_images[filename] = images if len(images) > 1 else images[0]

    # Read the tool README
    tool_readme = ""
    tool_readme_path = data_root / "tools" / "README.md"
    assert tool_readme_path.is_file(), "README.md is required for the tools"
    tool_readme = tool_readme_path.read_text()

    # Create the problem object and the seed object
    problem = Problem(
        metadata=ProblemMetaData(**metadata),
        constraints=constraints,
        statement=statement_en,
        statement_ja=statement_ja,
        statement_images=statement_images,
        example_input=example_input,
        example_output=example_output,
        tool_readme=tool_readme,
    )

    return problem, seeds, standings, rank_performance_map, data_root


def build_rust_tools(tool_cache_dir: Path) -> None:
    """Build the Rust tools.

    Args:
        tool_cache_dir (Path): Directory containing the Rust tools. Cargo.toml must be in the root directory.

    Raises:
        RuntimeError: If the build fails.
    """
    docker_client = docker.from_env()
    build_container = docker_client.containers.run(
        image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
        command="cargo build --release",
        remove=True,
        auto_remove=True,
        detach=True,
        environment={"RUSTFLAGS": "-Awarnings"},
        group_add=[os.getgid()],
        user=os.getuid(),
        volumes={str(tool_cache_dir): {"bind": ale_bench.constants.WORK_DIR, "mode": "rw"}},
        working_dir=ale_bench.constants.WORK_DIR,
    )
    build_container.wait()
    # Check if the build was successful
    if build_container.attrs["State"]["ExitCode"] != 0:
        raise RuntimeError("Failed to build the Rust tool.")
    docker_client.close()
    # Check if the build was successful
    for tool in ["gen", "tester", "vis"]:
        if not (tool_cache_dir / "src" / "bin" / f"{tool}.rs").is_file():
            continue
        tool_path = tool_cache_dir / "target" / "release" / tool
        assert tool_path.is_file() and tool_path.stat().st_size > 0, f"Failed to build the {tool} tool."


def start_visualization_server(visualization_server_dir: Path, port_num: int) -> DockerContainer:
    """Start the visualization server.

    Args:
        visualization_server_dir (Path): Directory containing the visualization server files.
        port_num (int): Port number for the visualization server.

    Returns:
        docker.models.containers.Container: The Docker container running the visualization server.
    """
    docker_client = docker.from_env()
    container = docker_client.containers.run(
        image=ale_bench.constants.VIS_SERVER_DOCKER_IMAGE,
        cpu_period=100000,
        cpu_quota=100000,  # 1 CPU
        detach=True,
        mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
        ports={"80/tcp": port_num},
        volumes={str(visualization_server_dir): {"bind": ale_bench.constants.VIS_SERVER_DIR, "mode": "ro"}},
    )
    return container


class RatingCalculator:
    """Rating calculator for ALE-Bench.

    https://img.atcoder.jp/file/AHC_rating_v2.pdf
    """

    S = 724.4744301
    R = 0.8271973364

    def __init__(self) -> None:
        """Initialize the rating calculator."""
        self.schedule = self.load_contest_schedule()

    def calculate_rating(self, performances: dict[str, int], final_contest: str) -> int:
        """Calculate the rating based on the performances.

        Args:
            performances (dict[str, int]): Dictionary of performances for each problem ID.
            final_contest (str): The ID of the final contest.

        Returns:
            int: The calculated rating.

        Raises:
            ValueError: If the performances dictionary is empty.
            ValueError: If the problem ID in the dictionary is not found in the contest schedule.
            ValueError: If the final contest is not found in the schedule.
        """
        if len(performances) == 0:
            raise ValueError("The performances dictionary cannot be empty.")
        for problem_id in performances.keys():
            if problem_id not in self.schedule:
                raise ValueError(f"Problem ID {problem_id} not found in the contest schedule.")
        if final_contest not in self.schedule:
            raise ValueError(f"Final contest {final_contest} not found in the contest schedule.")
        last_contest_end_at = self.schedule[final_contest][1]
        decayed_performances = []
        for problem_id, performance in performances.items():
            _start_at, end_at, weight = self.schedule[problem_id]
            if end_at > last_contest_end_at:
                continue  # NOTE: Only consider performances before the final contest
            decayed_performance = performance + 150 - 100 * (last_contest_end_at.date() - end_at.date()).days / 365
            for j in range(1, 101):
                augmented_performance = decayed_performance - self.S * math.log(j)
                decayed_performances.append((augmented_performance, weight))
        decayed_performances.sort(key=lambda x: x[0], reverse=True)
        total_weight = 0.0
        rating = 0.0
        for decayed_performance, weight in decayed_performances:
            rating += decayed_performance * (math.pow(self.R, total_weight) - math.pow(self.R, total_weight + weight))
            total_weight += weight
        if rating < 400:
            rating = 400 / math.exp((400 - rating) / 400)
        return round(rating)

    @staticmethod
    def load_contest_schedule() -> dict[str, tuple[dt.datetime, dt.datetime, float]]:
        """Load the contest schedule from the Hugging Face Hub.

        Returns:
            dict[str, tuple[dt.datetime, dt.datetime, float]]:
                A dictionary mapping problem IDs to their start / end times and performance weights.
        """
        local_data_dir = get_local_data_dir()
        if local_data_dir is None or not (local_data_dir / "schedule.csv").is_file():
            # Load the contest schedule from the Hugging Face Hub
            cache_dir = get_cache_dir()
            schedule_file_path = hf_hub_download(
                repo_id=ale_bench.constants.HUGGING_FACE_REPO,
                filename="schedule.csv",
                repo_type="dataset",
                cache_dir=cache_dir,
            )
        else:
            schedule_file_path = str(local_data_dir / "schedule.csv")
        df_schedule = pl.read_csv(schedule_file_path)
        df_schedule = df_schedule.with_columns(
            pl.col("start_at").str.to_datetime(time_zone="Asia/Tokyo"),
            pl.col("end_at").str.to_datetime(time_zone="Asia/Tokyo"),
        )
        return {
            row["problem_id"]: (row["start_at"], row["end_at"], row["weight"])
            for row in df_schedule.iter_rows(named=True)
        }


class RankingCalculator:
    """Ranking calculator for ALE-Bench."""

    def __init__(self, minimum_participation: int = 5) -> None:
        """Initialize the ranking calculator."""
        # Load the ranking data from the Hugging Face Hub or local cache
        local_data_dir = get_local_data_dir()
        if local_data_dir is None or not (local_data_dir / "ranking.csv").is_file():
            # Load the ranking from the Hugging Face Hub
            cache_dir = get_cache_dir()
            ranking_file_path = hf_hub_download(
                repo_id=ale_bench.constants.HUGGING_FACE_REPO,
                filename="ranking.csv",
                repo_type="dataset",
                cache_dir=cache_dir,
            )
        else:
            ranking_file_path = str(local_data_dir / "ranking.csv")
        df_ranking = pl.read_csv(ranking_file_path).filter(pl.col("competitions") >= minimum_participation)
        # Prepare member variables
        num_active_users = len(df_ranking)
        self.avg_perfs = df_ranking["avg_perf"].sort(descending=True).to_list()
        self.ratings = df_ranking["rating"].sort(descending=True).to_list()
        self.avg_perf_ranks, self.rating_ranks = [], []
        current_avg_perf, current_rating = 10000.0, 10000
        current_avg_perf_rank, current_rating_rank = 0, 0
        for idx, (avg_perf, rating) in enumerate(zip(self.avg_perfs, self.ratings), 1):
            if avg_perf != current_avg_perf:
                current_avg_perf_rank = idx
                current_avg_perf = avg_perf
            self.avg_perf_ranks.append(current_avg_perf_rank)
            if rating != current_rating:
                current_rating_rank = idx
                current_rating = rating
            self.rating_ranks.append(current_rating_rank)
        # Append the last entry for the average performance and rating
        self.avg_perfs.append(-1000.0)
        self.avg_perf_ranks.append(num_active_users + 1)
        self.ratings.append(0)
        self.rating_ranks.append(num_active_users + 1)

    def calculate_avg_perf_rank(self, avg_perf: float) -> int:
        """Calculate the rank based on the rating.

        Args:
            avg_perf (float): The average performance to calculate the rank for.

        Returns:
            int: The calculated rank.

        Raises:
            ValueError: If the rating is less than -1000.
        """
        if avg_perf < -1000:
            raise ValueError("The rating must be greater than or equal to -1000.")
        ok, ng = len(self.avg_perfs), -1
        while ok - ng > 1:
            mid = (ok + ng) // 2
            if avg_perf < self.avg_perfs[mid]:
                ng = mid
            elif avg_perf > self.avg_perfs[mid]:
                ok = mid
            else:  # Exactly matched
                return self.avg_perf_ranks[mid]
        if ok == len(self.avg_perfs):
            assert False, "Something went wrong: `ok` should be less than `len(self.avg_perfs)`."
        return self.avg_perf_ranks[ok]

    def calculate_rating_rank(self, rating: int) -> int:
        """Calculate the rank based on the rating.

        Args:
            rating (int): The rating to calculate the rank for.

        Returns:
            int: The calculated rank.

        Raises:
            ValueError: If the rating is less than 0.
        """
        if rating < 0:
            raise ValueError("The rating must be greater than or equal to 0.")
        ok, ng = len(self.ratings), -1
        while ok - ng > 1:
            mid = (ok + ng) // 2
            if rating < self.ratings[mid]:
                ng = mid
            elif rating > self.ratings[mid]:
                ok = mid
            else:  # Exactly matched
                return self.rating_ranks[mid]
        if ok == len(self.ratings):
            assert False, "Something went wrong: `ok` should be less than `len(self.ratings)`."
        return self.rating_ranks[ok]
