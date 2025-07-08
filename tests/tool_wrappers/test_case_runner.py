from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion, get_compile_command
from ale_bench.result import CaseResult, JudgeResult
from ale_bench.tool_wrappers.case_runner import (
    HostPathsBatchJudge,
    HostPathsBatchRun,
    HostPathsCompile,
    HostPathsReactiveJudge,
    HostPathsVis,
    build_batch_judge_command,
    build_batch_run_command,
    build_compile_command,
    build_reactive_judge_command,
    build_vis_command,
    get_batch_judge_volumes,
    get_batch_run_volumes,
    get_compile_volumes,
    get_reactive_judge_volumes,
    get_vis_volumes,
    parse_profiles,
    setup_paths_batch_judge,
    setup_paths_batch_run,
    setup_paths_compile,
    setup_paths_reactive_judge,
    setup_paths_vis,
)


@pytest.mark.parametrize(
    "code,code_language,judge_version",
    [
        pytest.param("cpp17", CodeLanguage.CPP17, JudgeVersion.V201907, id="cpp17-v201907"),
        pytest.param("python", CodeLanguage.PYTHON, JudgeVersion.V201907, id="python-v201907"),
        pytest.param("rust", CodeLanguage.RUST, JudgeVersion.V201907, id="rust-v201907"),
        pytest.param("cpp17", CodeLanguage.CPP17, JudgeVersion.V202301, id="cpp17-v202301"),
        pytest.param("cpp20", CodeLanguage.CPP20, JudgeVersion.V202301, id="cpp20-v202301"),
        pytest.param("cpp23", CodeLanguage.CPP23, JudgeVersion.V202301, id="cpp23-v202301"),
        pytest.param("python", CodeLanguage.PYTHON, JudgeVersion.V202301, id="python-v202301"),
        pytest.param("rust", CodeLanguage.RUST, JudgeVersion.V202301, id="rust-v202301"),
    ],
)
def test_setup_paths_compile(
    code: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        host_paths_compile = setup_paths_compile(temp_dir, code, code_language, judge_version)
        assert host_paths_compile.code_file.is_file()
        assert host_paths_compile.code_file.read_text() == code
        assert host_paths_compile.object_file.is_file()
        assert host_paths_compile.object_file.stat().st_size == 0


def test_get_compile_volumes() -> None:
    host_paths_compile = HostPathsCompile(
        code_file=Path("/tmp/test/code.cpp"), object_file=Path("/tmp/test/object.out")
    )
    compile_volumes = get_compile_volumes(host_paths_compile, Path("/tmp/test"))
    assert compile_volumes.keys() == {"/tmp/test/code.cpp", "/tmp/test/object.out"}
    assert compile_volumes["/tmp/test/code.cpp"]["bind"] == f"{ale_bench.constants.WORK_DIR}/code.cpp"
    assert compile_volumes["/tmp/test/code.cpp"]["mode"] == "ro"
    assert compile_volumes["/tmp/test/object.out"]["bind"] == "/tmp/object.out"
    assert compile_volumes["/tmp/test/object.out"]["mode"] == "rw"


def test_get_compile_volumes_nested() -> None:
    host_paths_compile = HostPathsCompile(
        code_file=Path("/tmp/test/src/main.rs"), object_file=Path("/tmp/test/target/release/main")
    )
    compile_volumes = get_compile_volumes(host_paths_compile, Path("/tmp/test"))
    assert compile_volumes.keys() == {"/tmp/test/src/main.rs", "/tmp/test/target/release/main"}
    assert compile_volumes["/tmp/test/src/main.rs"]["bind"] == f"{ale_bench.constants.WORK_DIR}/src/main.rs"
    assert compile_volumes["/tmp/test/src/main.rs"]["mode"] == "ro"
    assert compile_volumes["/tmp/test/target/release/main"]["bind"] == "/tmp/target/release/main"
    assert compile_volumes["/tmp/test/target/release/main"]["mode"] == "rw"


@pytest.mark.parametrize(
    "code_language,judge_version,object_file_relative_path_str",
    [
        pytest.param(CodeLanguage.CPP17, JudgeVersion.V201907, "cpp17", id="cpp17-v201907"),
        pytest.param(CodeLanguage.PYTHON, JudgeVersion.V201907, "python", id="python-v201907"),
        pytest.param(CodeLanguage.RUST, JudgeVersion.V201907, "rust", id="rust-v201907"),
        pytest.param(CodeLanguage.CPP17, JudgeVersion.V202301, "cpp17/202301", id="cpp17-v202301"),
        pytest.param(CodeLanguage.CPP20, JudgeVersion.V202301, "cpp20/202301", id="cpp20-v202301"),
        pytest.param(CodeLanguage.CPP23, JudgeVersion.V202301, "cpp23/202301", id="cpp23-v202301"),
        pytest.param(CodeLanguage.PYTHON, JudgeVersion.V202301, "python/202301", id="python-v202301"),
        pytest.param(CodeLanguage.RUST, JudgeVersion.V202301, "rust/202301", id="rust-v202301"),
    ],
)
def test_build_compile_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    object_file_relative_path_str: str,
) -> None:
    object_file_relative_path = Path(object_file_relative_path_str)
    command = get_compile_command(code_language, judge_version)
    build_command = build_compile_command(code_language, judge_version, object_file_relative_path)
    assert build_command == (
        f"{command}; "
        f"cp {ale_bench.constants.WORK_DIR}/{object_file_relative_path} /tmp/{object_file_relative_path_str}; "
        f"chmod 744 /tmp/{object_file_relative_path_str}"
    )


@pytest.mark.parametrize(
    "problem_id,case_idx,input_str,input_file_name,output_file_name,profiles_file_name",
    [
        pytest.param(
            "ahc001",
            0,
            "input",
            "ahc001_000000_input.txt",
            "ahc001_000000_output.txt",
            "ahc001_000000_profiles.json",
            id="ahc001-0",
        ),
        pytest.param(
            "ahc002",
            1,
            "tmp",
            "ahc002_000001_input.txt",
            "ahc002_000001_output.txt",
            "ahc002_000001_profiles.json",
            id="ahc002-1",
        ),
        pytest.param(
            "ahc003",
            10,
            "hoge",
            "ahc003_000010_input.txt",
            "ahc003_000010_output.txt",
            "ahc003_000010_profiles.json",
            id="ahc003-10",
        ),
        pytest.param(
            "ahc004",
            100,
            "C++17",
            "ahc004_000100_input.txt",
            "ahc004_000100_output.txt",
            "ahc004_000100_profiles.json",
            id="ahc004-100",
        ),
        pytest.param(
            "ahc005",
            999,
            "C++20",
            "ahc005_000999_input.txt",
            "ahc005_000999_output.txt",
            "ahc005_000999_profiles.json",
            id="ahc005-999",
        ),
        pytest.param(
            "future-contest-2022-qual",
            1000,
            "C++23",
            "future-contest-2022-qual_001000_input.txt",
            "future-contest-2022-qual_001000_output.txt",
            "future-contest-2022-qual_001000_profiles.json",
            id="future-contest-2022-qual-1000",
        ),
        pytest.param(
            "toyota2023summer-final",
            10000,
            "Python",
            "toyota2023summer-final_010000_input.txt",
            "toyota2023summer-final_010000_output.txt",
            "toyota2023summer-final_010000_profiles.json",
            id="toyota2023summer-final-10000",
        ),
        pytest.param(
            "ahc044",
            100000,
            "Rust",
            "ahc044_100000_input.txt",
            "ahc044_100000_output.txt",
            "ahc044_100000_profiles.json",
            id="ahc044-100000",
        ),
    ],
)
def test_setup_paths_batch_run(
    problem_id: str,
    case_idx: int,
    input_str: str,
    input_file_name: str,
    output_file_name: str,
    profiles_file_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        host_paths_compile = HostPathsCompile(code_file=temp_dir / "code.txt", object_file=temp_dir / "object.out")
        host_paths_run = setup_paths_batch_run(host_paths_compile, temp_dir, problem_id, case_idx, input_str)
        assert host_paths_run.code_file == host_paths_compile.code_file
        assert host_paths_run.object_file == host_paths_compile.object_file
        assert host_paths_run.input_file.name == input_file_name
        assert host_paths_run.input_file.is_file()
        assert host_paths_run.input_file.read_text() == input_str
        assert host_paths_run.output_file.name == output_file_name
        assert host_paths_run.output_file.is_file()
        assert host_paths_run.output_file.stat().st_size == 0
        assert host_paths_run.profiles_file.name == profiles_file_name
        assert host_paths_run.profiles_file.is_file()
        assert host_paths_run.profiles_file.stat().st_size == 0


def test_get_batch_run_volumes() -> None:
    host_paths_run = HostPathsBatchRun(
        code_file=Path("/tmp/test/code.cpp"),
        object_file=Path("/tmp/test/object.out"),
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        profiles_file=Path("/tmp/test/profiles.json"),
    )
    run_volumes = get_batch_run_volumes(host_paths_run, Path("/tmp/test"))
    assert run_volumes.keys() == {
        "/tmp/test/code.cpp",
        "/tmp/test/object.out",
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/test/profiles.json",
    }
    assert run_volumes["/tmp/test/code.cpp"]["bind"] == f"{ale_bench.constants.WORK_DIR}/code.cpp"
    assert run_volumes["/tmp/test/code.cpp"]["mode"] == "ro"
    assert run_volumes["/tmp/test/object.out"]["bind"] == f"{ale_bench.constants.WORK_DIR}/object.out"
    assert run_volumes["/tmp/test/object.out"]["mode"] == "ro"
    assert run_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert run_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert run_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert run_volumes["/tmp/test/output.txt"]["mode"] == "rw"
    assert run_volumes["/tmp/test/profiles.json"]["bind"] == ale_bench.constants.PROFILES_FILE
    assert run_volumes["/tmp/test/profiles.json"]["mode"] == "rw"


def test_get_batch_run_volumes_nested() -> None:
    host_paths_run = HostPathsBatchRun(
        code_file=Path("/tmp/test/src/main.rs"),
        object_file=Path("/tmp/test/target/release/main"),
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        profiles_file=Path("/tmp/test/profiles.json"),
    )
    run_volumes = get_batch_run_volumes(host_paths_run, Path("/tmp/test"))
    assert run_volumes.keys() == {
        "/tmp/test/src/main.rs",
        "/tmp/test/target/release/main",
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/test/profiles.json",
    }
    assert run_volumes["/tmp/test/src/main.rs"]["bind"] == f"{ale_bench.constants.WORK_DIR}/src/main.rs"
    assert run_volumes["/tmp/test/src/main.rs"]["mode"] == "ro"
    assert run_volumes["/tmp/test/target/release/main"]["bind"] == f"{ale_bench.constants.WORK_DIR}/target/release/main"
    assert run_volumes["/tmp/test/target/release/main"]["mode"] == "ro"
    assert run_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert run_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert run_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert run_volumes["/tmp/test/output.txt"]["mode"] == "rw"
    assert run_volumes["/tmp/test/profiles.json"]["bind"] == ale_bench.constants.PROFILES_FILE
    assert run_volumes["/tmp/test/profiles.json"]["mode"] == "rw"


@pytest.mark.parametrize(
    "code_language,judge_version,time_limit,expected",
    [
        pytest.param(
            CodeLanguage.CPP17,
            JudgeVersion.V201907,
            0.5,
            (
                "timeout 1.2 prlimit --cpu=1.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp17-v201907",
        ),
        pytest.param(
            CodeLanguage.PYTHON,
            JudgeVersion.V201907,
            0.1,
            (
                "timeout 1.2 prlimit --cpu=1.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"python3.8 Main.py < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="python-v201907",
        ),
        pytest.param(
            CodeLanguage.RUST,
            JudgeVersion.V201907,
            0.8,
            (
                "timeout 1.2 prlimit --cpu=1.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./target/release/main < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="rust-v201907",
        ),
        pytest.param(
            CodeLanguage.CPP17,
            JudgeVersion.V202301,
            1.0,
            (
                "timeout 2.2 prlimit --cpu=2.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp17-v202301",
        ),
        pytest.param(
            CodeLanguage.CPP20,
            JudgeVersion.V202301,
            1.9,
            (
                "timeout 2.2 prlimit --cpu=2.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp20-v202301",
        ),
        pytest.param(
            CodeLanguage.CPP23,
            JudgeVersion.V202301,
            1.9000001,
            (
                "timeout 3.2 prlimit --cpu=3.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp23-v202301",
        ),
        pytest.param(
            CodeLanguage.PYTHON,
            JudgeVersion.V202301,
            3.0,
            (
                "timeout 4.2 prlimit --cpu=4.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"python3.11 Main.py < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="python-v202301",
        ),
        pytest.param(
            CodeLanguage.RUST,
            JudgeVersion.V202301,
            5.0,
            (
                "timeout 6.2 prlimit --cpu=6.1 "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./target/release/main < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="rust-v202301",
        ),
    ],
)
def test_build_batch_run_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    expected: str,
) -> None:
    run_command = build_batch_run_command(code_language, judge_version, time_limit)
    assert run_command == expected


def test_setup_paths_batch_judge() -> None:
    host_paths_run = HostPathsBatchRun(
        code_file=Path("/tmp/test/code.cpp"),
        object_file=Path("/tmp/test/object.out"),
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        profiles_file=Path("/tmp/test/profiles.json"),
    )
    host_paths_judge = setup_paths_batch_judge(host_paths_run)
    assert host_paths_judge.input_file == host_paths_run.input_file
    assert host_paths_judge.output_file == host_paths_run.output_file
    assert host_paths_judge.profiles_file == host_paths_run.profiles_file


def test_get_batch_judge_volumes() -> None:
    host_paths_judge = HostPathsBatchJudge(
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        profiles_file=Path("/tmp/test/profiles.json"),
    )
    judge_volumes = get_batch_judge_volumes(host_paths_judge, Path("/tmp/cache"))
    assert judge_volumes.keys() == {
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/cache/tools/target/release/tester",
    }
    assert judge_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert judge_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert judge_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert judge_volumes["/tmp/test/output.txt"]["mode"] == "ro"
    assert judge_volumes["/tmp/cache/tools/target/release/tester"]["bind"] == ale_bench.constants.TESTER_BIN
    assert judge_volumes["/tmp/cache/tools/target/release/tester"]["mode"] == "ro"


def test_build_batch_judge_command() -> None:
    judge_command = build_batch_judge_command()
    assert judge_command == (
        f"{ale_bench.constants.TESTER_BIN} {ale_bench.constants.INPUT_FILE} {ale_bench.constants.OUTPUT_FILE}"
    )


@pytest.mark.parametrize(
    "problem_id,case_idx,input_str,input_file_name,output_file_name,profiles_file_name",
    [
        pytest.param(
            "ahc001",
            0,
            "input",
            "ahc001_000000_input.txt",
            "ahc001_000000_output.txt",
            "ahc001_000000_profiles.json",
            id="ahc001-0",
        ),
        pytest.param(
            "ahc002",
            1,
            "tmp",
            "ahc002_000001_input.txt",
            "ahc002_000001_output.txt",
            "ahc002_000001_profiles.json",
            id="ahc002-1",
        ),
        pytest.param(
            "ahc003",
            10,
            "hoge",
            "ahc003_000010_input.txt",
            "ahc003_000010_output.txt",
            "ahc003_000010_profiles.json",
            id="ahc003-10",
        ),
        pytest.param(
            "ahc004",
            100,
            "C++17",
            "ahc004_000100_input.txt",
            "ahc004_000100_output.txt",
            "ahc004_000100_profiles.json",
            id="ahc004-100",
        ),
        pytest.param(
            "ahc005",
            999,
            "C++20",
            "ahc005_000999_input.txt",
            "ahc005_000999_output.txt",
            "ahc005_000999_profiles.json",
            id="ahc005-999",
        ),
        pytest.param(
            "future-contest-2022-qual",
            1000,
            "C++23",
            "future-contest-2022-qual_001000_input.txt",
            "future-contest-2022-qual_001000_output.txt",
            "future-contest-2022-qual_001000_profiles.json",
            id="future-contest-2022-qual-1000",
        ),
        pytest.param(
            "toyota2023summer-final",
            10000,
            "Python",
            "toyota2023summer-final_010000_input.txt",
            "toyota2023summer-final_010000_output.txt",
            "toyota2023summer-final_010000_profiles.json",
            id="toyota2023summer-final-10000",
        ),
        pytest.param(
            "ahc044",
            100000,
            "Rust",
            "ahc044_100000_input.txt",
            "ahc044_100000_output.txt",
            "ahc044_100000_profiles.json",
            id="ahc044-100000",
        ),
    ],
)
def test_setup_paths_reactive_judge(
    problem_id: str,
    case_idx: int,
    input_str: str,
    input_file_name: str,
    output_file_name: str,
    profiles_file_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        host_paths_compile = HostPathsCompile(code_file=temp_dir / "code.txt", object_file=temp_dir / "object.out")
        host_paths_run = setup_paths_reactive_judge(host_paths_compile, temp_dir, problem_id, case_idx, input_str)
        assert host_paths_run.code_file == host_paths_compile.code_file
        assert host_paths_run.object_file == host_paths_compile.object_file
        assert host_paths_run.input_file.name == input_file_name
        assert host_paths_run.input_file.is_file()
        assert host_paths_run.input_file.read_text() == input_str
        assert host_paths_run.output_file.name == output_file_name
        assert host_paths_run.output_file.is_file()
        assert host_paths_run.output_file.stat().st_size == 0
        assert host_paths_run.profiles_file.name == profiles_file_name
        assert host_paths_run.profiles_file.is_file()
        assert host_paths_run.profiles_file.stat().st_size == 0


def test_get_reactive_judge_volumes() -> None:
    host_paths_run = HostPathsReactiveJudge(
        code_file=Path("/tmp/test/code.cpp"),
        object_file=Path("/tmp/test/object.out"),
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        profiles_file=Path("/tmp/test/profiles.json"),
    )
    run_volumes = get_reactive_judge_volumes(host_paths_run, Path("/tmp/test"), Path("/tmp/cache"))
    assert run_volumes.keys() == {
        "/tmp/test/code.cpp",
        "/tmp/test/object.out",
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/test/profiles.json",
        "/tmp/cache/tools/target/release/tester",
    }
    assert run_volumes["/tmp/test/code.cpp"]["bind"] == f"{ale_bench.constants.WORK_DIR}/code.cpp"
    assert run_volumes["/tmp/test/code.cpp"]["mode"] == "ro"
    assert run_volumes["/tmp/test/object.out"]["bind"] == f"{ale_bench.constants.WORK_DIR}/object.out"
    assert run_volumes["/tmp/test/object.out"]["mode"] == "ro"
    assert run_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert run_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert run_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert run_volumes["/tmp/test/output.txt"]["mode"] == "rw"
    assert run_volumes["/tmp/test/profiles.json"]["bind"] == ale_bench.constants.PROFILES_FILE
    assert run_volumes["/tmp/test/profiles.json"]["mode"] == "rw"
    assert run_volumes["/tmp/cache/tools/target/release/tester"]["bind"] == ale_bench.constants.TESTER_BIN
    assert run_volumes["/tmp/cache/tools/target/release/tester"]["mode"] == "ro"


def test_get_reactive_judge_volumes_nested() -> None:
    host_paths_run = HostPathsReactiveJudge(
        code_file=Path("/tmp/test/src/main.rs"),
        object_file=Path("/tmp/test/target/release/main"),
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        profiles_file=Path("/tmp/test/profiles.json"),
    )
    run_volumes = get_reactive_judge_volumes(host_paths_run, Path("/tmp/test"), Path("/tmp/cache"))
    assert run_volumes.keys() == {
        "/tmp/test/src/main.rs",
        "/tmp/test/target/release/main",
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/test/profiles.json",
        "/tmp/cache/tools/target/release/tester",
    }
    assert run_volumes["/tmp/test/src/main.rs"]["bind"] == f"{ale_bench.constants.WORK_DIR}/src/main.rs"
    assert run_volumes["/tmp/test/src/main.rs"]["mode"] == "ro"
    assert run_volumes["/tmp/test/target/release/main"]["bind"] == f"{ale_bench.constants.WORK_DIR}/target/release/main"
    assert run_volumes["/tmp/test/target/release/main"]["mode"] == "ro"
    assert run_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert run_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert run_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert run_volumes["/tmp/test/output.txt"]["mode"] == "rw"
    assert run_volumes["/tmp/test/profiles.json"]["bind"] == ale_bench.constants.PROFILES_FILE
    assert run_volumes["/tmp/test/profiles.json"]["mode"] == "rw"
    assert run_volumes["/tmp/cache/tools/target/release/tester"]["bind"] == ale_bench.constants.TESTER_BIN
    assert run_volumes["/tmp/cache/tools/target/release/tester"]["mode"] == "ro"


@pytest.mark.parametrize(
    "code_language,judge_version,time_limit,expected",
    [
        pytest.param(
            CodeLanguage.CPP17,
            JudgeVersion.V201907,
            0.9,
            (
                "timeout 1.2 prlimit --cpu=1.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="python-v201907",
        ),
        pytest.param(
            CodeLanguage.PYTHON,
            JudgeVersion.V201907,
            0.7,
            (
                "timeout 1.2 prlimit --cpu=1.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"python3.8 Main.py < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="python-v201907",
        ),
        pytest.param(
            CodeLanguage.RUST,
            JudgeVersion.V201907,
            0.90001,
            (
                "timeout 2.2 prlimit --cpu=2.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./target/release/main < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="rust-v201907",
        ),
        pytest.param(
            CodeLanguage.CPP17,
            JudgeVersion.V202301,
            1.5,
            (
                "timeout 2.2 prlimit --cpu=2.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp17-v202301",
        ),
        pytest.param(
            CodeLanguage.CPP20,
            JudgeVersion.V202301,
            1.90000,
            (
                "timeout 2.2 prlimit --cpu=2.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp20-v202301",
        ),
        pytest.param(
            CodeLanguage.CPP23,
            JudgeVersion.V202301,
            2.0,
            (
                "timeout 3.2 prlimit --cpu=3.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./a.out < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="cpp23-v202301",
        ),
        pytest.param(
            CodeLanguage.PYTHON,
            JudgeVersion.V202301,
            3.5,
            (
                "timeout 4.2 prlimit --cpu=4.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"python3.11 Main.py < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="python-v202301",
        ),
        pytest.param(
            CodeLanguage.RUST,
            JudgeVersion.V202301,
            10.0,
            (
                "timeout 11.2 prlimit --cpu=11.1 "
                f"{ale_bench.constants.TESTER_BIN} "
                f'/usr/bin/time -f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" -o {ale_bench.constants.PROFILES_FILE} '
                f"./target/release/main < {ale_bench.constants.INPUT_FILE} > {ale_bench.constants.OUTPUT_FILE}; sync"
            ),
            id="rust-v202301",
        ),
    ],
)
def test_build_reactive_judge_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    expected: str,
) -> None:
    run_command = build_reactive_judge_command(code_language, judge_version, time_limit)
    assert run_command == expected


@pytest.mark.parametrize(
    "problem_id,case_idx,local_visualization_file_name",
    [
        pytest.param(
            "ahc001",
            0,
            "ahc001_000000_local_visualization.html",
            id="ahc001-0",
        ),
        pytest.param(
            "ahc002",
            1,
            "ahc002_000001_local_visualization.svg",
            id="ahc002-1",
        ),
        pytest.param(
            "ahc003",
            10,
            "ahc003_000010_local_visualization.svg",
            id="ahc003-10",
        ),
        pytest.param(
            "ahc004",
            100,
            "ahc004_000100_local_visualization.svg",
            id="ahc004-100",
        ),
        pytest.param(
            "ahc005",
            999,
            "ahc005_000999_local_visualization.svg",
            id="ahc005-999",
        ),
        pytest.param(
            "future-contest-2022-qual",
            1000,
            "future-contest-2022-qual_001000_local_visualization.svg",
            id="future-contest-2022-qual-1000",
        ),
        pytest.param(
            "ahc007",
            9999,
            "ahc007_009999_local_visualization.svg",
            id="ahc007-9999",
        ),
        pytest.param(
            "ahc008",
            10000,
            "ahc008_010000_local_visualization.html",
            id="ahc008-10000",
        ),
        pytest.param(
            "toyota2023summer-final",
            99999,
            "toyota2023summer-final_099999_local_visualization.html",
            id="toyota2023summer-final-99999",
        ),
        pytest.param(
            "ahc044",
            100000,
            "ahc044_100000_local_visualization.html",
            id="ahc044-100000",
        ),
    ],
)
def test_setup_paths_vis(
    problem_id: str,
    case_idx: int,
    local_visualization_file_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        host_paths_run_batch = HostPathsBatchJudge(
            input_file=temp_dir / f"{problem_id}_{case_idx:06d}_input.txt",
            output_file=temp_dir / f"{problem_id}_{case_idx:06d}_output.txt",
            profiles_file=temp_dir / f"{problem_id}_{case_idx:06d}_profiles.json",
        )
        host_paths_vis = setup_paths_vis(host_paths_run_batch, temp_dir, problem_id, case_idx)
        assert host_paths_vis.input_file == host_paths_run_batch.input_file
        assert host_paths_vis.output_file == host_paths_run_batch.output_file
        assert host_paths_vis.local_visualization_file.name == local_visualization_file_name
        assert host_paths_vis.local_visualization_file.is_file()
        assert host_paths_vis.local_visualization_file.stat().st_size == 0

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        host_paths_run_reactive = HostPathsReactiveJudge(
            code_file=temp_dir / "code.txt",
            object_file=temp_dir / "object.out",
            input_file=temp_dir / f"{problem_id}_{case_idx:06d}_input.txt",
            output_file=temp_dir / f"{problem_id}_{case_idx:06d}_output.txt",
            profiles_file=temp_dir / f"{problem_id}_{case_idx:06d}_profiles.json",
        )
        host_paths_vis = setup_paths_vis(host_paths_run_reactive, temp_dir, problem_id, case_idx)
        assert host_paths_vis.input_file == host_paths_run_reactive.input_file
        assert host_paths_vis.output_file == host_paths_run_reactive.output_file
        assert host_paths_vis.local_visualization_file.name == local_visualization_file_name
        assert host_paths_vis.local_visualization_file.is_file()
        assert host_paths_vis.local_visualization_file.stat().st_size == 0


def test_get_vis_volumes_svg() -> None:
    host_paths_vis = HostPathsVis(
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        local_visualization_file=Path("/tmp/test/local_visualization.svg"),
    )
    vis_volumes = get_vis_volumes(host_paths_vis, Path("/tmp/cache"))
    assert vis_volumes.keys() == {
        "/tmp/cache/tools/target/release/vis",
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/test/local_visualization.svg",
    }
    assert vis_volumes["/tmp/cache/tools/target/release/vis"]["bind"] == ale_bench.constants.VIS_BIN
    assert vis_volumes["/tmp/cache/tools/target/release/vis"]["mode"] == "ro"
    assert vis_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert vis_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert vis_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert vis_volumes["/tmp/test/output.txt"]["mode"] == "ro"
    assert vis_volumes["/tmp/test/local_visualization.svg"]["bind"] == ale_bench.constants.LOCAL_VIS_SVG
    assert vis_volumes["/tmp/test/local_visualization.svg"]["mode"] == "rw"


def test_get_vis_volumes_html() -> None:
    host_paths_vis = HostPathsVis(
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        local_visualization_file=Path("/tmp/test/local_visualization.html"),
    )
    vis_volumes = get_vis_volumes(host_paths_vis, Path("/tmp/cache"))
    assert vis_volumes.keys() == {
        "/tmp/cache/tools/target/release/vis",
        "/tmp/test/input.txt",
        "/tmp/test/output.txt",
        "/tmp/test/local_visualization.html",
    }
    assert vis_volumes["/tmp/cache/tools/target/release/vis"]["bind"] == ale_bench.constants.VIS_BIN
    assert vis_volumes["/tmp/cache/tools/target/release/vis"]["mode"] == "ro"
    assert vis_volumes["/tmp/test/input.txt"]["bind"] == ale_bench.constants.INPUT_FILE
    assert vis_volumes["/tmp/test/input.txt"]["mode"] == "ro"
    assert vis_volumes["/tmp/test/output.txt"]["bind"] == ale_bench.constants.OUTPUT_FILE
    assert vis_volumes["/tmp/test/output.txt"]["mode"] == "ro"
    assert vis_volumes["/tmp/test/local_visualization.html"]["bind"] == ale_bench.constants.LOCAL_VIS_HTML
    assert vis_volumes["/tmp/test/local_visualization.html"]["mode"] == "rw"


def test_get_vis_volumes_error() -> None:
    host_paths_vis = HostPathsVis(
        input_file=Path("/tmp/test/input.txt"),
        output_file=Path("/tmp/test/output.txt"),
        local_visualization_file=Path("/tmp/test/local_visualization.txt"),
    )
    with pytest.raises(ValueError, match=r"The local visualization file must have either \.svg or \.html extension\."):
        get_vis_volumes(host_paths_vis, Path("/tmp/cache"))


def test_build_vis_command() -> None:
    vis_command = build_vis_command()
    assert (
        vis_command
        == f"{ale_bench.constants.VIS_BIN} {ale_bench.constants.INPUT_FILE} {ale_bench.constants.OUTPUT_FILE}"
    )


sample_profiles_content = """{{
    "command": "dummy command",
    "exit_status": "{}",
    "elapsed_time": "{}",
    "elapsed_time_seconds": "{}",
    "system_cpu_seconds": "{}",
    "user_cpu_seconds": "{}",
    "cpu_percent": "100%",
    "average_resident_set_size_kbytes": "0",
    "max_resident_set_size_kbytes": "{}",
    "average_total_memory_kbytes": "0",
    "signals_delivered": "0",
    "page_size_bytes": "4096",
    "minor_page_faults": "128",
    "major_page_faults": "0",
    "swaps": "0",
    "file_system_inputs": "0",
    "file_system_outputs": "0",
    "average_shared_text_kbytes": "0",
    "average_unshared_data_kbytes": "0",
    "average_unshared_stack_kbytes": "0",
    "voluntary_context_switches": "0",
    "involuntary_context_switches": "0",
    "socket_messages_sent": "0",
    "socket_messages_received": "0"
}}"""


@pytest.mark.parametrize(
    "time_limit,memory_limit,execution_time_host,profiles_content,expected",
    [
        pytest.param(
            2.0,
            1073741824,
            2.01,
            "",
            CaseResult(
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.01,
                memory_usage=0,
            ),
            id="empty_tle",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.2,
            "",
            CaseResult(
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.1,
                memory_usage=0,
            ),
            id="empty_tle_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            0.9,
            "",
            CaseResult(
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=0.9,
                memory_usage=0,
            ),
            id="empty_re",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.0,
            "",
            CaseResult(
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.0,
                memory_usage=0,
            ),
            id="empty_re_time_limit",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384")[:-10],
            CaseResult(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="Wrong answer.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="broken_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.2,
            sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384")[:-10],
            CaseResult(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="Wrong answer.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.1,
                memory_usage=0,
            ),
            id="broken_wa_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command terminated by signal 9.\n"
                f"{sample_profiles_content.format('0', '0:02.23', '2.23', '0.23', '2.00', '16384')[:-10]}"
            ),
            CaseResult(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="Wrong answer.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="killed_broken_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command exited with non-zero status.\n"
                f"{sample_profiles_content.format('0', '0:02.23', '2.23', '0.23', '2.00', '16384')[:-10]}"
            ),
            CaseResult(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="Wrong answer.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="non_aero_exited_broken_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command terminated by signal 9.\n.\n"
                f"{sample_profiles_content.format('0', '0:02.23', '2.23', '0.23', '2.00', '16384')[:-10]}"
            ),
            CaseResult(
                judge_result=JudgeResult.WRONG_ANSWER,
                message="Wrong answer.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="invalid_profiles_content_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            "\n".join(sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384").splitlines()[:-3])
            + '    "socket_messages_received": "0"\n}\n',
            CaseResult(
                judge_result=JudgeResult.INTERNAL_ERROR,
                message="Internal Error: Invalid profiles format.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="invalid_profiles_format_ie",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.11,
            "\n".join(sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384").splitlines()[:-3])
            + '    "socket_messages_received": "0"\n}\n',
            CaseResult(
                judge_result=JudgeResult.INTERNAL_ERROR,
                message="Internal Error: Invalid profiles format.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.1,
                memory_usage=0,
            ),
            id="invalid_profiles_format_ie_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("1", "0:01.23", "1.23", "0.23", "1.00", "16384"),
            CaseResult(
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=1.23,
                memory_usage=16777216,
            ),
            id="exited_non_zero_status_re",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("9", "0:02.23", "2.23", "0.23", "1.00", "16384"),
            CaseResult(
                judge_result=JudgeResult.RUNTIME_ERROR,
                message="Runtime error.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.1,
                memory_usage=16777216,
            ),
            id="exited_non_zero_status_re_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.01", "2.01", "0.01", "2.00", "16384"),
            CaseResult(
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.01,
                memory_usage=16777216,
            ),
            id="tle",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384"),
            CaseResult(
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.1,
                memory_usage=16777216,
            ),
            id="tle_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.01", "2.01", "0.01", "2.00", "1048577"),
            CaseResult(
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.01,
                memory_usage=1073742848,
            ),
            id="tle_too_many_memory",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command terminated by signal 9.\n"
                f"{sample_profiles_content.format('0', '0:02.00', '2.00', '0.00', '2.00', '16384')}"
            ),
            CaseResult(
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.00,
                memory_usage=16777216,
            ),
            id="killed_tle",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "1048577"),
            CaseResult(
                judge_result=JudgeResult.MEMORY_LIMIT_EXCEEDED,
                message="Memory limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=2.00,
                memory_usage=1073742848,
            ),
            id="mle",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "16384"),
            (2.0, 16777216),
            id="ac",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "1048576"),
            (2.0, 1073741824),
            id="ac_memory_limit",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.01,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "1048576"),
            (2.0, 1073741824),
            id="ac_ignore_host_time",
        ),
    ],
)
def test_parse_profiles(
    time_limit: float,
    memory_limit: int,
    execution_time_host: float,
    profiles_content: str,
    expected: CaseResult | tuple[float, int],
) -> None:
    assert parse_profiles(time_limit, memory_limit, profiles_content, execution_time_host, None, None, None) == expected
