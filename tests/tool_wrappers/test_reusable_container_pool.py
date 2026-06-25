from pathlib import Path

import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.data import ProblemType
from ale_bench.tool_wrappers.reusable_container_pool import (
    REUSABLE_SUBMISSION_TMP_DIR,
    REUSABLE_TOOL_TMP_DIR,
    ReusableSubmissionContainerPool,
    ReusableToolContainerPool,
    get_reusable_submission_volumes,
    get_reusable_tool_volumes,
)

TMP_TEST_DIR = f"{ale_bench.constants.TMP_DIR}/test"
TMP_CACHE_DIR = f"{ale_bench.constants.TMP_DIR}/cache"


def test_get_reusable_submission_volumes_batch() -> None:
    reusable_volumes = get_reusable_submission_volumes(
        Path(TMP_TEST_DIR),
        Path(f"{TMP_TEST_DIR}/case-files"),
        Path(TMP_CACHE_DIR),
        ProblemType.BATCH,
    )
    assert reusable_volumes == {
        TMP_TEST_DIR: {"bind": ale_bench.constants.WORK_DIR, "mode": "ro"},
        f"{TMP_TEST_DIR}/case-files": {
            "bind": REUSABLE_SUBMISSION_TMP_DIR,
            "mode": "rw",
        },
    }


def test_get_reusable_submission_volumes_reactive() -> None:
    reusable_volumes = get_reusable_submission_volumes(
        Path(TMP_TEST_DIR),
        Path(f"{TMP_TEST_DIR}/case-files"),
        Path(TMP_CACHE_DIR),
        ProblemType.REACTIVE,
    )
    assert reusable_volumes == {
        TMP_TEST_DIR: {"bind": ale_bench.constants.WORK_DIR, "mode": "ro"},
        f"{TMP_TEST_DIR}/case-files": {
            "bind": REUSABLE_SUBMISSION_TMP_DIR,
            "mode": "rw",
        },
        f"{TMP_CACHE_DIR}/tools/target/release/tester": {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
    }


def test_reusable_submission_container_pool_container_path() -> None:
    scratch_dir = Path(f"{TMP_TEST_DIR}/case-files")
    pool = ReusableSubmissionContainerPool(
        code_language=CodeLanguage.PYTHON,
        judge_version=JudgeVersion.V202301,
        temp_dir=Path(TMP_TEST_DIR),
        scratch_dir=scratch_dir,
        tool_dir=Path(TMP_CACHE_DIR),
        problem_type=ProblemType.BATCH,
        num_workers=1,
    )

    assert (
        pool.container_path(scratch_dir / "ahc001_000000_input.txt")
        == f"{REUSABLE_SUBMISSION_TMP_DIR}/ahc001_000000_input.txt"
    )


def test_get_reusable_tool_volumes() -> None:
    reusable_volumes = get_reusable_tool_volumes(
        Path(f"{TMP_TEST_DIR}/case-files"),
        Path(TMP_CACHE_DIR),
    )
    assert reusable_volumes == {
        f"{TMP_TEST_DIR}/case-files": {
            "bind": REUSABLE_TOOL_TMP_DIR,
            "mode": "rw",
        },
        f"{TMP_CACHE_DIR}/tools/target/release/tester": {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
        f"{TMP_CACHE_DIR}/tools/target/release/vis": {
            "bind": ale_bench.constants.VIS_BIN,
            "mode": "ro",
        },
    }


def test_reusable_tool_container_pool_container_path() -> None:
    scratch_dir = Path(f"{TMP_TEST_DIR}/case-files")
    pool = ReusableToolContainerPool(
        scratch_dir=scratch_dir,
        tool_dir=Path(TMP_CACHE_DIR),
        num_workers=1,
    )

    assert (
        pool.container_path(scratch_dir / "ahc001_000000_output.txt")
        == f"{REUSABLE_TOOL_TMP_DIR}/ahc001_000000_output.txt"
    )
