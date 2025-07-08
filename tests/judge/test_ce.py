from pathlib import Path

import pytest

import ale_bench
import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.data import ProblemType
from ale_bench.result import JudgeResult
from ale_bench.session import Session
from ale_bench.tool_wrappers import run_cases


@pytest.mark.docker
class TestCE:
    CODES_ROOT = Path(__file__).resolve().parent / "codes"
    INPUTS_ROOT = Path(__file__).resolve().parent / "inputs"

    @pytest.fixture(scope="class")
    def ahc001_session(self) -> Session:
        return ale_bench.start("ahc001", lite_version=False)

    @pytest.fixture(scope="class")
    def ahc003_session(self) -> Session:
        return ale_bench.start("ahc003", lite_version=False)

    @pytest.fixture(scope="class")
    def inputs(self) -> dict[str, str]:
        return {
            "ahc001": (self.INPUTS_ROOT / "ahc001.txt").read_text(),
            "ahc003": (self.INPUTS_ROOT / "ahc003.txt").read_text(),
        }

    @pytest.fixture(scope="class")
    def ce_codes(self) -> dict[CodeLanguage, str]:
        return {
            CodeLanguage.CPP17: (self.CODES_ROOT / "ce_cpp17.cpp").read_text(),
            CodeLanguage.CPP20: (self.CODES_ROOT / "ce_cpp20.cpp").read_text(),
            CodeLanguage.CPP23: (self.CODES_ROOT / "ce_cpp23.cpp").read_text(),
            CodeLanguage.PYTHON: (self.CODES_ROOT / "ce_python.py").read_text(),
            CodeLanguage.RUST: (self.CODES_ROOT / "ce_rust.rs").read_text(),
        }

    @pytest.mark.parametrize(
        "code_language,judge_version",
        [
            pytest.param(CodeLanguage.CPP17, JudgeVersion.V201907, id="cpp17-v201907"),
            pytest.param(CodeLanguage.CPP17, JudgeVersion.V202301, id="cpp17-v202301"),
            pytest.param(CodeLanguage.CPP20, JudgeVersion.V202301, id="cpp20-v202301"),
            pytest.param(CodeLanguage.CPP23, JudgeVersion.V202301, id="cpp23-v202301"),
            pytest.param(CodeLanguage.PYTHON, JudgeVersion.V201907, id="python-v201907"),
            pytest.param(CodeLanguage.PYTHON, JudgeVersion.V202301, id="python-v202301"),
            pytest.param(CodeLanguage.RUST, JudgeVersion.V201907, id="rust-v201907"),
            pytest.param(CodeLanguage.RUST, JudgeVersion.V202301, id="rust-v202301"),
        ],
    )
    def test_ce_batch(
        self,
        code_language: CodeLanguage,
        judge_version: JudgeVersion,
        inputs: dict[str, str],
        ce_codes: dict[CodeLanguage, str],
        ahc001_session: Session,
    ) -> None:
        problem_id = "ahc001"
        input_str = inputs[problem_id]

        case_results = run_cases(
            inputs=[input_str],
            code=ce_codes[code_language],
            code_language=code_language,
            judge_version=judge_version,
            time_limit=2.0,
            memory_limit=256 * 1024 * 1024,  # 256 MiB
            problem_id=problem_id,
            problem_type=ProblemType.BATCH,
            tool_dir=ahc001_session.tool_dir,
            return_details=True,
            skip_local_visualization=False,
            num_workers=1,
        )
        assert len(case_results) == 1
        for case_result in case_results:
            assert case_result.input_str is None, f"{case_result.input_str} is not None"
            assert case_result.output_str is None, f"{case_result.output_str} is not None"
            assert case_result.judge_result == JudgeResult.COMPILATION_ERROR, (
                f"{case_result.judge_result} != COMPILATION_ERROR"
            )
            assert case_result.absolute_score == ale_bench.constants.REJECTED_ABSOLUTE_SCORE, (
                f"{case_result.absolute_score} != {ale_bench.constants.REJECTED_ABSOLUTE_SCORE}"
            )
            assert case_result.relative_score is None, f"{case_result.relative_score} is not None"
            assert case_result.local_visualization is None, f"{case_result.local_visualization} is not None"

    @pytest.mark.parametrize(
        "code_language,judge_version",
        [
            pytest.param(CodeLanguage.CPP17, JudgeVersion.V201907, id="cpp17-v201907"),
            pytest.param(CodeLanguage.CPP17, JudgeVersion.V202301, id="cpp17-v202301"),
            pytest.param(CodeLanguage.CPP20, JudgeVersion.V202301, id="cpp20-v202301"),
            pytest.param(CodeLanguage.CPP23, JudgeVersion.V202301, id="cpp23-v202301"),
            pytest.param(CodeLanguage.PYTHON, JudgeVersion.V201907, id="python-v201907"),
            pytest.param(CodeLanguage.PYTHON, JudgeVersion.V202301, id="python-v202301"),
            pytest.param(CodeLanguage.RUST, JudgeVersion.V201907, id="rust-v201907"),
            pytest.param(CodeLanguage.RUST, JudgeVersion.V202301, id="rust-v202301"),
        ],
    )
    def test_ce_reactive(
        self,
        code_language: CodeLanguage,
        judge_version: JudgeVersion,
        inputs: dict[str, str],
        ce_codes: dict[CodeLanguage, str],
        ahc003_session: Session,
    ) -> None:
        problem_id = "ahc003"
        input_str = inputs[problem_id]
        num_cases = 4
        num_workers = 2

        case_results = run_cases(
            inputs=[input_str] * num_cases,
            code=ce_codes[code_language],
            code_language=code_language,
            judge_version=judge_version,
            time_limit=2.0,
            memory_limit=256 * 1024 * 1024,  # 256 MiB
            problem_id=problem_id,
            problem_type=ProblemType.REACTIVE,
            tool_dir=ahc003_session.tool_dir,
            return_details=False,
            skip_local_visualization=True,
            num_workers=num_workers,
        )
        assert len(case_results) == num_cases
        for case_result in case_results:
            assert case_result.input_str is None, f"{case_result.input_str} is not None"
            assert case_result.output_str is None, f"{case_result.output_str} is not None"
            assert case_result.judge_result == JudgeResult.COMPILATION_ERROR, (
                f"{case_result.judge_result} != COMPILATION_ERROR"
            )
            assert case_result.absolute_score == ale_bench.constants.REJECTED_ABSOLUTE_SCORE, (
                f"{case_result.absolute_score} != {ale_bench.constants.REJECTED_ABSOLUTE_SCORE}"
            )
            assert case_result.relative_score is None, f"{case_result.relative_score} is not None"
            assert case_result.local_visualization is None, f"{case_result.local_visualization} is not None"
