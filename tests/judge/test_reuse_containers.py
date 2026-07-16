from collections.abc import Generator
from pathlib import Path

import pytest

import ale_bench
import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.data import ProblemType
from ale_bench.result import CaseResult, JudgeResult
from ale_bench.session import Session
from ale_bench.tool_wrappers import run_cases


@pytest.mark.docker
class TestReuseContainers:
    CODES_ROOT = Path(__file__).resolve().parent / "codes"
    INPUTS_ROOT = Path(__file__).resolve().parent / "inputs"
    CODE_LANGUAGE = CodeLanguage.CPP20
    JUDGE_VERSION = JudgeVersion.V202301
    SCORE_RELATIVE_TOLERANCE = 0.005

    @pytest.fixture(scope="class")
    def ahc001_session(self) -> Generator[Session, None, None]:
        session = ale_bench.start("ahc001", lite_version=False)
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture(scope="class")
    def ahc003_session(self) -> Generator[Session, None, None]:
        session = ale_bench.start("ahc003", lite_version=False)
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture(scope="class")
    def inputs(self) -> dict[str, str]:
        return {
            "ahc001": (self.INPUTS_ROOT / "ahc001.txt").read_text(),
            "ahc003": (self.INPUTS_ROOT / "ahc003.txt").read_text(),
        }

    @pytest.fixture(scope="class")
    def ac_codes(self) -> dict[str, str]:
        return {
            "ahc001": (self.CODES_ROOT / "ac_cpp20_ahc001.cpp").read_text(),
            "ahc003": (self.CODES_ROOT / "ac_cpp20_ahc003.cpp").read_text(),
        }

    @classmethod
    def assert_scores_close(cls, default_results: list[CaseResult], reused_results: list[CaseResult]) -> None:
        for default_result, reused_result in zip(default_results, reused_results, strict=True):
            assert default_result.absolute_score > ale_bench.constants.REJECTED_ABSOLUTE_SCORE
            assert reused_result.absolute_score > ale_bench.constants.REJECTED_ABSOLUTE_SCORE
            score_denominator = max(default_result.absolute_score, reused_result.absolute_score)
            relative_diff = abs(default_result.absolute_score - reused_result.absolute_score) / score_denominator
            assert relative_diff <= cls.SCORE_RELATIVE_TOLERANCE

    def test_reuse_containers_matches_default_batch(
        self,
        inputs: dict[str, str],
        ac_codes: dict[str, str],
        ahc001_session: Session,
    ) -> None:
        input_str = inputs["ahc001"]
        common_kwargs = {
            "inputs": [input_str, input_str],
            "code": ac_codes["ahc001"],
            "code_language": self.CODE_LANGUAGE,
            "judge_version": self.JUDGE_VERSION,
            "time_limit": 5.0,
            "memory_limit": 256 * 1024 * 1024,
            "problem_id": "ahc001",
            "problem_type": ProblemType.BATCH,
            "tool_dir": ahc001_session.tool_dir,
            "return_details": True,
            "skip_local_visualization": False,
            "num_workers": 2,
        }

        default_results = run_cases(**common_kwargs, reuse_containers=False)
        reused_results = run_cases(**common_kwargs, reuse_containers=True)

        assert [result.judge_result for result in default_results] == [JudgeResult.ACCEPTED, JudgeResult.ACCEPTED]
        assert [result.judge_result for result in reused_results] == [JudgeResult.ACCEPTED, JudgeResult.ACCEPTED]
        self.assert_scores_close(default_results, reused_results)
        assert all(result.local_visualization is not None for result in default_results)
        assert all(result.local_visualization is not None for result in reused_results)

    def test_reuse_containers_handles_unsafe_problem_id_characters(
        self,
        inputs: dict[str, str],
        ac_codes: dict[str, str],
        ahc001_session: Session,
    ) -> None:
        results = run_cases(
            inputs=[inputs["ahc001"]],
            code=ac_codes["ahc001"],
            code_language=self.CODE_LANGUAGE,
            judge_version=self.JUDGE_VERSION,
            time_limit=5.0,
            memory_limit=256 * 1024 * 1024,
            problem_id=r"problem/name (variant); $(command)&",
            problem_type=ProblemType.BATCH,
            tool_dir=ahc001_session.tool_dir,
            return_details=True,
            skip_local_visualization=True,
            num_workers=1,
            reuse_containers=True,
        )

        assert [result.judge_result for result in results] == [JudgeResult.ACCEPTED]

    def test_reuse_containers_matches_default_reactive(
        self,
        inputs: dict[str, str],
        ac_codes: dict[str, str],
        ahc003_session: Session,
    ) -> None:
        input_str = inputs["ahc003"]
        common_kwargs = {
            "inputs": [input_str, input_str],
            "code": ac_codes["ahc003"],
            "code_language": self.CODE_LANGUAGE,
            "judge_version": self.JUDGE_VERSION,
            "time_limit": 2.0,
            "memory_limit": 256 * 1024 * 1024,
            "problem_id": "ahc003",
            "problem_type": ProblemType.REACTIVE,
            "tool_dir": ahc003_session.tool_dir,
            "return_details": False,
            "skip_local_visualization": False,
            "num_workers": 2,
        }

        default_results = run_cases(**common_kwargs, reuse_containers=False)
        reused_results = run_cases(**common_kwargs, reuse_containers=True)

        assert [result.judge_result for result in default_results] == [JudgeResult.ACCEPTED, JudgeResult.ACCEPTED]
        assert [result.judge_result for result in reused_results] == [JudgeResult.ACCEPTED, JudgeResult.ACCEPTED]
        self.assert_scores_close(default_results, reused_results)
        assert all(result.local_visualization is not None for result in default_results)
        assert all(result.local_visualization is not None for result in reused_results)
