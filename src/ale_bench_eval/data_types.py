from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ale_bench_eval.prompts.builder import PromptArgs


class Solution(BaseModel):
    """Represents a code solution with its metadata."""

    name: str = Field(..., min_length=1, description="Human-readable name for the solution")
    code: str = Field(..., min_length=0, description="The source code of the solution")
    code_language: Literal["any", "python", "cpp17", "cpp20", "cpp23", "rust", ""] = Field(
        ..., description="Programming language of the solution"
    )


@dataclass
class EvaluationConfig:
    model_name: str
    n_repeated_sampling: int
    n_self_refine: int
    num_workers: int
    n_public_cases: int | None
    prompt_args: PromptArgs
    problem_id: str
    lite_version: bool
    root_path: Path | None = None
