from typing import Literal
from unittest.mock import MagicMock

import pytest
from PIL import Image
from pydantic_ai import BinaryContent

from ale_bench.data import ScoreType
from ale_bench.result import CaseResult, JudgeResult, ResourceUsage, Result
from ale_bench_eval.data_types import EvaluationConfig
from ale_bench_eval.prompts.builder import (
    PromptArgs,
    create_budget_action_message,
    create_feedback_message,
    diagnostic_feedback,
    parse_budget_action,
)
from ale_bench_eval.scaffolds import _build_refinement_user_prompt, _pick_crossover_parents, _truncate_population
from ale_bench_eval.selection import select_worst_case_indices


def make_case_result(
    absolute_score: int,
    judge_result: JudgeResult = JudgeResult.ACCEPTED,
    input_str: str | None = "10 20\n0 1 2",
    output_str: str | None = "3\n",
) -> CaseResult:
    return CaseResult(
        input_str=input_str,
        output_str=output_str,
        judge_result=judge_result,
        message="",
        absolute_score=absolute_score,
        execution_time=1.0,
        memory_usage=1024 * 1024,
    )


def make_result(case_results: list[CaseResult]) -> Result:
    return Result(allow_score_non_ac=True, resource_usage=ResourceUsage(), case_results=case_results)


def make_prompt_args(prompt_language: Literal["en", "ja"] = "en") -> PromptArgs:
    return PromptArgs(
        code_language="cpp20",
        judge_version="202301",
        prompt_language=prompt_language,
        use_image=False,
    )


def make_config(
    *,
    feedback_diagnostic: bool = False,
    feedback_visualization: bool = False,
    n_feedback_worst_cases: int = 3,
) -> EvaluationConfig:
    return EvaluationConfig(
        model_name="test-model",
        n_repeated_sampling=1,
        n_self_refine=1,
        num_workers=1,
        reuse_containers=False,
        n_public_cases=None,
        prompt_args=make_prompt_args(),
        problem_id="ahc001",
        lite_version=True,
        feedback_diagnostic=feedback_diagnostic,
        feedback_visualization=feedback_visualization,
        n_feedback_worst_cases=n_feedback_worst_cases,
    )


@pytest.mark.parametrize(
    ("scores", "score_type", "k", "expected"),
    [
        pytest.param([10, 30, 20], ScoreType.MAXIMIZE, 2, [0, 2], id="maximize_lowest_first"),
        pytest.param([10, 30, 20], ScoreType.MINIMIZE, 2, [1, 2], id="minimize_highest_first"),
        pytest.param([10, 30, 20], ScoreType.MAXIMIZE, 10, [0, 2, 1], id="k_exceeds_length"),
        pytest.param([5, 5, 5], ScoreType.MAXIMIZE, 2, [0, 1], id="ties_prefer_lower_index"),
    ],
)
def test_select_worst_case_indices(scores: list[int], score_type: ScoreType, k: int, expected: list[int]) -> None:
    case_results = [make_case_result(score) for score in scores]
    assert select_worst_case_indices(case_results, score_type, k) == expected


def test_select_worst_case_indices_non_ac_ranks_worst() -> None:
    case_results = [
        make_case_result(1, judge_result=JudgeResult.ACCEPTED),
        make_case_result(1000, judge_result=JudgeResult.TIME_LIMIT_EXCEEDED),
        make_case_result(2, judge_result=JudgeResult.ACCEPTED),
    ]
    assert select_worst_case_indices(case_results, ScoreType.MAXIMIZE, 2) == [1, 0]


@pytest.mark.parametrize("prompt_language", ["en", "ja"])
def test_diagnostic_feedback_contents(prompt_language: Literal["en", "ja"]) -> None:
    result = make_result(
        [
            make_case_result(100, input_str="7 3\nrest"),
            make_case_result(5, input_str=None),
            make_case_result(50, judge_result=JudgeResult.WRONG_ANSWER),
        ]
    )
    feedback = diagnostic_feedback(make_prompt_args(prompt_language), result, worst_indices=[1, 2])
    assert 'Case 1: params="7 3", score=100' in feedback
    assert 'Case 2: params="N/A", score=5 (WORST)' in feedback
    assert 'Case 3: params="10 20", score=50, judge=WRONG_ANSWER (WORST)' in feedback
    assert "score=100 (WORST)" not in feedback  # Case 1 is not marked as worst


def test_create_feedback_message_backward_compatible() -> None:
    args = make_prompt_args()
    result = make_result([make_case_result(100)])
    message = create_feedback_message(args, result)
    assert len(message) == 1
    assert isinstance(message[0], str)
    assert "Overall absolute score: 100" in message[0]
    # No result available (e.g. no code block found in the response)
    no_result_message = create_feedback_message(args, None)
    assert len(no_result_message) == 1
    assert isinstance(no_result_message[0], str)
    assert "No public result is available" in no_result_message[0]


def test_create_feedback_message_with_diagnostic_and_visualizations() -> None:
    args = make_prompt_args()
    result = make_result([make_case_result(100)])
    image = BinaryContent(data=b"fake-png", media_type="image/png")
    message = create_feedback_message(
        args,
        result,
        diagnostic="\n[Per-case diagnostics]\ncase table",
        visualizations=[image],
        visualized_case_indices=[0],
    )
    assert len(message) == 3
    assert isinstance(message[0], str)
    assert "[Per-case diagnostics]" in message[0]
    assert "worst-scoring cases: 1" in message[0]
    assert message[1] is image
    assert isinstance(message[2], str)


def make_mock_session(problem_id: str, score_type: ScoreType = ScoreType.MAXIMIZE) -> MagicMock:
    session = MagicMock()
    session.problem.metadata.problem_id = problem_id
    session.problem.metadata.score_type = score_type
    return session


def test_build_refinement_user_prompt_defaults_to_plain_feedback() -> None:
    config = make_config()
    session = make_mock_session("ahc001")
    result = make_result([make_case_result(100)])
    message = _build_refinement_user_prompt(config, session, result, MagicMock())
    assert message == create_feedback_message(config.prompt_args, result)
    session.local_visualization.assert_not_called()


def test_build_refinement_user_prompt_skips_visualization_for_no_local_vis() -> None:
    config = make_config(feedback_visualization=True)
    session = make_mock_session("ahc016")
    result = make_result([make_case_result(100)])
    message = _build_refinement_user_prompt(config, session, result, MagicMock())
    session.local_visualization.assert_not_called()
    assert all(not isinstance(content, BinaryContent) for content in message)


def test_build_refinement_user_prompt_renders_and_drops_none_images() -> None:
    config = make_config(feedback_visualization=True, n_feedback_worst_cases=2)
    session = make_mock_session("ahc001")
    session.local_visualization.return_value = [None, Image.new("RGB", (4, 4))]
    result = make_result([make_case_result(10), make_case_result(20), make_case_result(30)])
    message = _build_refinement_user_prompt(config, session, result, MagicMock())
    (called_inputs, called_outputs), _ = session.local_visualization.call_args
    assert len(called_inputs) == len(called_outputs) == 2
    images = [content for content in message if isinstance(content, BinaryContent)]
    assert len(images) == 1
    # The surviving image belongs to case index 1 (the second-worst case)
    assert isinstance(message[0], str)
    assert "worst-scoring cases: 2" in message[0]


def test_build_refinement_user_prompt_visualization_failure_degrades() -> None:
    config = make_config(feedback_visualization=True)
    session = make_mock_session("ahc001")
    session.local_visualization.side_effect = RuntimeError("docker down")
    result = make_result([make_case_result(100)])
    message = _build_refinement_user_prompt(config, session, result, MagicMock())
    assert all(not isinstance(content, BinaryContent) for content in message)


def make_population_entry(score: int, code: str = "int main() {}") -> dict[str, int | str]:
    return {"code": code, "overall_absolute_score": score}


def test_truncate_population_orders_best_first_and_drops_empty_code() -> None:
    entries = [
        (("repeated_sampling", 0), make_population_entry(10)),
        (("repeated_sampling", 1), make_population_entry(30)),
        (("evolution", 1), make_population_entry(999, code="  ")),
        (("evolution", 2), make_population_entry(20)),
    ]
    population = _truncate_population(entries, 2, ScoreType.MAXIMIZE)
    assert [key for key, _ in population] == [("repeated_sampling", 1), ("evolution", 2)]
    population = _truncate_population(entries, 2, ScoreType.MINIMIZE)
    assert [key for key, _ in population] == [("repeated_sampling", 0), ("evolution", 2)]


def test_truncate_population_is_deterministic_on_ties() -> None:
    entries = [
        (("repeated_sampling", 1), make_population_entry(10)),
        (("evolution", 1), make_population_entry(10)),
        (("repeated_sampling", 0), make_population_entry(10)),
    ]
    population = _truncate_population(entries, 3, ScoreType.MAXIMIZE)
    assert [key for key, _ in population] == [
        ("evolution", 1),
        ("repeated_sampling", 0),
        ("repeated_sampling", 1),
    ]


def test_pick_crossover_parents_is_score_diverse() -> None:
    population = [
        (("repeated_sampling", 0), make_population_entry(100)),
        (("evolution", 1), make_population_entry(90)),
        (("evolution", 2), make_population_entry(10)),
    ]
    best, partner = _pick_crossover_parents(population)
    assert best[0] == ("repeated_sampling", 0)
    assert partner[0] == ("evolution", 2)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param("ACTION: SAMPLE\nTrying a new idea.", "sample", id="sample"),
        pytest.param("ACTION: REFINE\nKeep improving.", "refine", id="refine"),
        pytest.param("action: sample", "sample", id="case_insensitive"),
        pytest.param("I considered ACTION: SAMPLE but decided on\nACTION: REFINE", "refine", id="last_match_wins"),
        pytest.param("Let me think about it...", "refine", id="unparseable_defaults_to_refine"),
        pytest.param("", "refine", id="empty_defaults_to_refine"),
    ],
)
def test_parse_budget_action(response: str, expected: str) -> None:
    assert parse_budget_action(response) == expected


def test_create_budget_action_message_contents() -> None:
    message = create_budget_action_message(
        make_prompt_args(),
        remaining_budget=7,
        history_rows=[(0, "initial", 100), (1, "sample", 120), (2, "refine", 130)],
    )
    assert "7 calls left" in message
    assert "- Attempt 0 (initial): score=100" in message
    assert "- Attempt 2 (refine): score=130" in message
    assert "ACTION: SAMPLE" in message
    assert "ACTION: REFINE" in message
