import base64
import dataclasses
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel
from pydantic_ai.run import AgentRunResult

from ale_bench.constants import ALLOW_SCORE_NON_AC_PRIVATE
from ale_bench.result import CaseResult, ResourceUsage, Result as AleBenchResult
from ale_bench.schemas import ResultSerializable as AleBenchResultSerializable

UTC: Final[datetime.tzinfo] = getattr(datetime, "UTC", datetime.timezone.utc)


def get_now_utc() -> datetime.datetime:
    return datetime.datetime.now(tz=UTC)


def get_now_utc_string() -> str:
    return get_now_utc().strftime("%Y-%m-%d_%H-%M-%S")


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        match obj:
            case bytes():
                return {
                    "__type__": "bytes",
                    "encoding": "base64",
                    "data": base64.b64encode(obj).decode("ascii"),
                }
            case datetime.datetime():
                return {"__type__": "datetime", "data": obj.isoformat()}
        return super().default(obj)


class CustomJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj: Any) -> Any:
        match obj:
            case {"__type__": "bytes", "encoding": "base64", "data": data}:
                return base64.b64decode(data)
            case {"__type__": "datetime", "data": data}:
                return datetime.datetime.fromisoformat(data)
        return obj


class Logger:
    def __init__(self, path_to_log: str, problem_id: str = "") -> None:
        base_logger = logging.getLogger(__name__ + "_" + problem_id)
        if not base_logger.handlers:
            base_logger.setLevel(logging.INFO)

            formatter = logging.Formatter(
                "%(asctime)s - %(problem_id)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            file_handler = logging.FileHandler(path_to_log)
            file_handler.setFormatter(formatter)
            base_logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            base_logger.addHandler(console_handler)

            base_logger.propagate = False

        self.logger = logging.LoggerAdapter(base_logger, {"problem_id": problem_id})

    def info(self, message: object) -> None:
        self.logger.info(message)

    def warning(self, message: object) -> None:
        self.logger.warning(message)

    def error(self, message: object) -> None:
        self.logger.error(message)


# NOTE: AgentRunResult is a dataclass, which does not support recursive deserialization
class AgentRunResultWrapper(BaseModel):
    value: AgentRunResult


class SaveInfo:
    def __init__(self, model_name: str, problem_id: str, root_path: Path | None = None) -> None:
        self.problem_id = problem_id
        if root_path is None:
            self.problem_root = Path.cwd() / f"results/{model_name}_{get_now_utc_string()}" / problem_id
        else:
            self.problem_root = root_path / problem_id
        self.problem_root.mkdir(parents=True, exist_ok=True)
        self.conversations = self.problem_root / "conversations"
        self.conversations.mkdir(parents=True, exist_ok=True)
        self.results = self.problem_root / "results"
        self.results.mkdir(parents=True, exist_ok=True)
        self.ale_bench_results = self.problem_root / "ale_bench_results"
        self.ale_bench_results.mkdir(parents=True, exist_ok=True)
        self.logger = Logger(str(self.problem_root / "logs.txt"), problem_id=problem_id)

    def save_conversations(self, filename: str, agent_run_result: AgentRunResult) -> None:
        """Save conversations to JSON file."""
        with open(self.conversations / filename, "w") as f:
            json.dump(dataclasses.asdict(agent_run_result), f, cls=CustomJSONEncoder)

    def load_conversations(self, filename: str) -> AgentRunResult:
        """Load conversations from JSON file."""
        with open(self.conversations / filename, "r") as f:
            data = json.load(f, cls=CustomJSONDecoder)
        return AgentRunResultWrapper.model_validate({"value": data}).value

    def save_results(self, filename: str, results: dict[str, Any]) -> None:
        """Save results to JSON file."""
        with open(self.results / filename, "w") as f:
            json.dump(results, f)

    def load_results(self, filename: str) -> dict[str, Any]:
        """Load results from JSON file."""
        with open(self.results / filename, "r") as f:
            result = json.load(f)
        if not isinstance(result, dict):
            raise ValueError(f"Invalid result format: {type(result)}")
        return result

    def save_ale_bench_results(self, filename: str, results: AleBenchResult) -> None:
        """Save results to JSON file."""
        serialized_results = AleBenchResultSerializable.from_result(
            AleBenchResult(
                allow_score_non_ac=self.problem_id in ALLOW_SCORE_NON_AC_PRIVATE,
                resource_usage=results.resource_usage,
                case_results=results.case_results,
            )
        )
        with open(self.ale_bench_results / filename, "w") as f:
            json.dump(serialized_results.model_dump(), f)

    def load_ale_bench_results(self, filename: str) -> AleBenchResult:
        """Load results from JSON file."""
        with open(self.ale_bench_results / filename, "r") as f:
            ale_bench_result = json.load(f)
        return AleBenchResult(
            allow_score_non_ac=self.problem_id in ALLOW_SCORE_NON_AC_PRIVATE,
            resource_usage=ResourceUsage(**ale_bench_result["resource_usage"]),
            case_results=[CaseResult(**case_result) for case_result in ale_bench_result["case_results"]],
        )
