from __future__ import annotations

import datetime
from typing import Any

import pytest
from PIL import Image

from ale_bench.data import ProblemConstraints, ProblemMetaData, ProblemType, ScoreType
from ale_bench.result import CaseResult, JudgeResult, ResourceUsage, Result
from ale_bench.schemas import CaseResultSerializable, ProblemSerializable, ResultSerializable
from ale_bench.utils import pil_to_base64


@pytest.mark.parametrize(
    "problem,serialized",
    [
        pytest.param(
            ProblemSerializable(
                metadata=ProblemMetaData(
                    problem_id="test",
                    start_at=datetime.datetime(2025, 1, 1, 0, 0, 0),
                    end_at=datetime.datetime(2025, 7, 7, 0, 0, 0),
                    contest_url="https://example.com/test",
                    title="Test Problem",
                    problem_type=ProblemType.BATCH,
                    score_type=ScoreType.MAXIMIZE,
                ),
                constraints=ProblemConstraints(
                    time_limit=2.0,
                    memory_limit=1073741824,
                ),
                statement="Test problem statement. Image:\nimage1\nVideo:\nvideo1",
                statement_ja="テスト問題文。画像:\nimage1\n映像:\nvideo1",
                statement_images={
                    "image1": Image.new("RGBA", (100, 100)),
                    "video1": [Image.new("RGBA", (100, 100), (64 * i,) * 4) for i in range(3)],
                },
                example_input="Test input",
                example_output="Test output",
                tool_readme="Test tool README",
            ),
            {
                "metadata": {
                    "problem_id": "test",
                    "start_at": "2025-01-01T00:00:00",
                    "end_at": "2025-07-07T00:00:00",
                    "contest_url": "https://example.com/test",
                    "title": "Test Problem",
                    "problem_type": "batch",
                    "score_type": "maximize",
                },
                "constraints": {
                    "time_limit": 2.0,
                    "memory_limit": 1073741824,
                },
                "statement": "Test problem statement. Image:\nimage1\nVideo:\nvideo1",
                "statement_ja": "テスト問題文。画像:\nimage1\n映像:\nvideo1",
                "statement_images": {
                    "image1": pil_to_base64(Image.new("RGBA", (100, 100))),
                    "video1": [pil_to_base64(Image.new("RGBA", (100, 100), (64 * i,) * 4)) for i in range(3)],
                },
                "example_input": "Test input",
                "example_output": "Test output",
                "tool_readme": "Test tool README",
            },
            id="problem_serializable_with_image",
        ),
    ],
)
def test_problem_serializable(problem: ProblemSerializable, serialized: dict[str, Any]) -> None:
    """Test serialization and deserialization of ProblemSerializable."""
    # Test serialization to dict
    problem_serialized = problem.model_dump()
    assert problem_serialized == serialized
    # Test deserialization from dict
    problem_restored = ProblemSerializable.model_validate(serialized)
    assert problem_restored == problem


@pytest.mark.parametrize(
    "case_result,serialized",
    [
        pytest.param(
            CaseResultSerializable(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="",
                absolute_score=0,
                local_visualization=None,
                execution_time=0.0,
                memory_usage=0,
            ),
            {
                "input_str": None,
                "output_str": None,
                "error_str": None,
                "judge_result": "WRONG_ANSWER",
                "message": "",
                "absolute_score": 0,
                "relative_score": None,
                "local_visualization": None,
                "execution_time": 0.0,
                "memory_usage": 0,
            },
            id="case_result_wrong_answer_no_visualization",
        ),
        pytest.param(
            CaseResultSerializable(
                input_str="input",
                output_str="output",
                error_str="error",
                judge_result=JudgeResult.ACCEPTED,
                message="message",
                absolute_score=100,
                relative_score=1,
                local_visualization=Image.new("RGBA", (100, 100)),
                execution_time=1.0,
                memory_usage=1024,
            ),
            {
                "input_str": "input",
                "output_str": "output",
                "error_str": "error",
                "judge_result": "ACCEPTED",
                "message": "message",
                "absolute_score": 100,
                "relative_score": 1,
                "local_visualization": pil_to_base64(Image.new("RGBA", (100, 100))),
                "execution_time": 1.0,
                "memory_usage": 1024,
            },
            id="case_result_accepted_with_visualization",
        ),
    ],
)
def test_case_result_serializable(
    case_result: CaseResultSerializable, serialized: dict[str, str | int | float | Image.Image]
) -> None:
    """Test serialization and deserialization of CaseResultSerializable."""
    # Test serialization to dict
    case_result_serialized = case_result.model_dump()
    assert case_result_serialized == serialized
    # Test deserialization from dict
    case_result_restored = CaseResultSerializable.model_validate(serialized)
    assert case_result_restored == case_result


@pytest.mark.parametrize(
    "case_result,expected",
    [
        pytest.param(
            CaseResult(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="",
                absolute_score=0,
                local_visualization=None,
                execution_time=0.0,
                memory_usage=0,
            ),
            CaseResultSerializable(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="",
                absolute_score=0,
                local_visualization=None,
                execution_time=0.0,
                memory_usage=0,
            ),
            id="case_result_wrong_answer_no_visualization",
        ),
        pytest.param(
            CaseResult(
                input_str="input",
                output_str="output",
                error_str="error",
                judge_result=JudgeResult.ACCEPTED,
                message="message",
                absolute_score=100,
                relative_score=1,
                local_visualization=Image.new("RGBA", (100, 100)),
                execution_time=1.0,
                memory_usage=1024,
            ),
            CaseResultSerializable(
                input_str="input",
                output_str="output",
                error_str="error",
                judge_result=JudgeResult.ACCEPTED,
                message="message",
                absolute_score=100,
                relative_score=1,
                local_visualization=Image.new("RGBA", (100, 100)),
                execution_time=1.0,
                memory_usage=1024,
            ),
            id="case_result_accepted_with_visualization",
        ),
    ],
)
def test_case_result_serializable_from_case_result(case_result: CaseResult, expected: CaseResultSerializable) -> None:
    """Test serialization and deserialization of CaseResultSerializable."""
    case_result_converted = CaseResultSerializable.from_case_result(case_result)
    assert case_result_converted == expected


@pytest.mark.parametrize(
    "result,expected",
    [
        pytest.param(
            Result(
                allow_score_non_ac=True,
                resource_usage=ResourceUsage(),
                case_results=[
                    CaseResult(
                        judge_result=JudgeResult.WRONG_ANSWER,
                        message="",
                        absolute_score=0,
                        local_visualization=None,
                        execution_time=0.0,
                        memory_usage=0,
                    ),
                    CaseResult(
                        input_str="input",
                        output_str="output",
                        error_str="error",
                        judge_result=JudgeResult.ACCEPTED,
                        message="message",
                        absolute_score=100,
                        relative_score=1,
                        local_visualization=Image.new("RGBA", (100, 100)),
                        execution_time=1.0,
                        memory_usage=1024,
                    ),
                ],
            ),
            ResultSerializable(
                allow_score_non_ac=True,
                resource_usage=ResourceUsage(),
                case_results=[
                    CaseResultSerializable(
                        judge_result=JudgeResult.WRONG_ANSWER,
                        message="",
                        absolute_score=0,
                        local_visualization=None,
                        execution_time=0.0,
                        memory_usage=0,
                    ),
                    CaseResultSerializable(
                        input_str="input",
                        output_str="output",
                        error_str="error",
                        judge_result=JudgeResult.ACCEPTED,
                        message="message",
                        absolute_score=100,
                        relative_score=1,
                        local_visualization=Image.new("RGBA", (100, 100)),
                        execution_time=1.0,
                        memory_usage=1024,
                    ),
                ],
            ),
            id="result_mixed",
        ),
    ],
)
def test_result_serializable_from_result(result: Result, expected: ResultSerializable) -> None:
    """Test serialization and deserialization of ResultSerializable."""
    result_converted = ResultSerializable.from_result(result)
    assert result_converted == expected
