from __future__ import annotations

import pytest
from PIL import Image

from ale_bench.result import CaseResult, JudgeResult, ResourceUsage, Result
from ale_bench.schemas import CaseResultSerializable, ResultSerializable
from ale_bench.utils import pil_to_base64


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
