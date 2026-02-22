import pytest

import ale_bench.constants
from ale_bench.code_language import (
    CodeLanguage,
    JudgeVersion,
    get_compile_command,
    get_docker_image_name,
    get_object_file_path,
    get_run_command,
    get_submission_file_path,
)


@pytest.mark.parametrize(
    ("code_language", "judge_version"),
    [
        pytest.param(CodeLanguage.CPP17, JudgeVersion.V201907, id="cpp17-v201907"),
        pytest.param(CodeLanguage.PYTHON, JudgeVersion.V201907, id="python-v201907"),
        pytest.param(CodeLanguage.RUST, JudgeVersion.V201907, id="rust-v201907"),
        pytest.param(CodeLanguage.CPP17, JudgeVersion.V202301, id="cpp17-v202301"),
        pytest.param(CodeLanguage.CPP20, JudgeVersion.V202301, id="cpp20-v202301"),
        pytest.param(CodeLanguage.CPP23, JudgeVersion.V202301, id="cpp23-v202301"),
        pytest.param(CodeLanguage.PYTHON, JudgeVersion.V202301, id="python-v202301"),
        pytest.param(CodeLanguage.RUST, JudgeVersion.V202301, id="rust-v202301"),
        pytest.param(CodeLanguage.BASH, JudgeVersion.V202510, id="bash-v202510"),
        pytest.param(CodeLanguage.CPP23, JudgeVersion.V202510, id="cpp23-v202510"),
        pytest.param(CodeLanguage.CSHARP, JudgeVersion.V202510, id="csharp-v202510"),
        pytest.param(CodeLanguage.FISH, JudgeVersion.V202510, id="fish-v202510"),
        pytest.param(CodeLanguage.FORTRAN, JudgeVersion.V202510, id="fortran-v202510"),
        pytest.param(CodeLanguage.GO, JudgeVersion.V202510, id="go-v202510"),
        pytest.param(CodeLanguage.HASKELL, JudgeVersion.V202510, id="haskell-v202510"),
        pytest.param(CodeLanguage.JAVASCRIPT, JudgeVersion.V202510, id="javascript-v202510"),
        pytest.param(CodeLanguage.JULIA, JudgeVersion.V202510, id="julia-v202510"),
        pytest.param(CodeLanguage.LEAN, JudgeVersion.V202510, id="lean-v202510"),
        pytest.param(CodeLanguage.OCAML, JudgeVersion.V202510, id="ocaml-v202510"),
        pytest.param(CodeLanguage.PERL, JudgeVersion.V202510, id="perl-v202510"),
        pytest.param(CodeLanguage.PYPY, JudgeVersion.V202510, id="pypy-v202510"),
        pytest.param(CodeLanguage.PYTHON, JudgeVersion.V202510, id="python-v202510"),
        pytest.param(CodeLanguage.RUST, JudgeVersion.V202510, id="rust-v202510"),
        pytest.param(CodeLanguage.TYPESCRIPT, JudgeVersion.V202510, id="typescript-v202510"),
    ],
)
def test_get_docker_image_name(code_language: CodeLanguage, judge_version: JudgeVersion) -> None:
    image_name = get_docker_image_name(code_language, judge_version)
    assert image_name == f"{ale_bench.constants.DOCKER_HUB_REPO}:{code_language.value}-{judge_version.value}"


def test_cpp23_202510_compile_command() -> None:
    command = get_compile_command(CodeLanguage.CPP23, JudgeVersion.V202510)
    assert "export PATH=/opt/gcc-15.2.0/bin:$PATH" in command
    assert "-flto=auto" in command
    assert 'g++ ./Main.cpp -o a.out "${USER_BUILD_FLAGS[@]}"' in command


def test_python_202510_command_and_paths() -> None:
    compile_command = get_compile_command(CodeLanguage.PYTHON, JudgeVersion.V202510)
    run_command = get_run_command(CodeLanguage.PYTHON, JudgeVersion.V202510)
    submission_file_path = get_submission_file_path(CodeLanguage.PYTHON, JudgeVersion.V202510)
    object_file_path = get_object_file_path(CodeLanguage.PYTHON, JudgeVersion.V202510)
    assert compile_command == "python3.13 -m py_compile Main.py; python3.13 Main.py ONLINE_JUDGE 2> /dev/null"
    assert run_command == "python3.13 -X int_max_str_digits=0 Main.py"
    assert submission_file_path == "Main.py"
    assert object_file_path == "__pycache__/Main.cpython-313.pyc"


def test_typescript_202510_command_and_paths() -> None:
    compile_command = get_compile_command(CodeLanguage.TYPESCRIPT, JudgeVersion.V202510)
    run_command = get_run_command(CodeLanguage.TYPESCRIPT, JudgeVersion.V202510)
    submission_file_path = get_submission_file_path(CodeLanguage.TYPESCRIPT, JudgeVersion.V202510)
    object_file_path = get_object_file_path(CodeLanguage.TYPESCRIPT, JudgeVersion.V202510)
    assert "tsc Main.ts" in compile_command
    assert run_command == "sh node.sh 1048576 Main.js ONLINE_JUDGE ATCODER"
    assert submission_file_path == "Main.ts"
    assert object_file_path == "Main.js"


@pytest.mark.parametrize(
    ("code_language", "submission_file_path", "object_file_path", "run_command"),
    [
        pytest.param(CodeLanguage.BASH, "Main.bash", "ok", "bash Main.bash", id="bash"),
        pytest.param(CodeLanguage.CSHARP, "Main.cs", "publish/Main.dll", "dotnet publish/Main.dll", id="csharp"),
        pytest.param(CodeLanguage.FISH, "Main.fish", "ok", "fish Main.fish", id="fish"),
        pytest.param(CodeLanguage.FORTRAN, "Main.f90", "a.out", "./a.out", id="fortran"),
        pytest.param(CodeLanguage.GO, "main.go", "a.out", "./a.out", id="go"),
        pytest.param(CodeLanguage.HASKELL, "submission/app/Main.hs", "main", "./main", id="haskell"),
        pytest.param(
            CodeLanguage.JAVASCRIPT,
            "Main.js",
            "ok",
            "sh node.sh 1048576 Main.js ONLINE_JUDGE ATCODER",
            id="javascript",
        ),
        pytest.param(
            CodeLanguage.JULIA,
            "Main.jl",
            "ok",
            "julia --threads=auto --startup-file=no --history-file=no Main.jl",
            id="julia",
        ),
        pytest.param(
            CodeLanguage.LEAN,
            "atcoder/Main.lean",
            "atcoder/.lake/build/bin/atcoder",
            "./atcoder/.lake/build/bin/atcoder",
            id="lean",
        ),
        pytest.param(CodeLanguage.OCAML, "main.ml", "a.out", "./a.out", id="ocaml"),
        pytest.param(CodeLanguage.PERL, "Main.pl", "ok", "perl Main.pl", id="perl"),
        pytest.param(
            CodeLanguage.PYPY,
            "Main.py",
            "__pycache__/Main.pypy311.pyc",
            "pypy3 -X int_max_str_digits=0 Main.py",
            id="pypy",
        ),
        pytest.param(
            CodeLanguage.RUST,
            "src/main.rs",
            "target/release/main",
            "./target/release/main",
            id="rust",
        ),
        pytest.param(
            CodeLanguage.TYPESCRIPT,
            "Main.ts",
            "Main.js",
            "sh node.sh 1048576 Main.js ONLINE_JUDGE ATCODER",
            id="typescript",
        ),
    ],
)
def test_202510_additional_language_paths_and_run_command(
    code_language: CodeLanguage,
    submission_file_path: str,
    object_file_path: str,
    run_command: str,
) -> None:
    assert get_compile_command(code_language, JudgeVersion.V202510)
    assert get_submission_file_path(code_language, JudgeVersion.V202510) == submission_file_path
    assert get_object_file_path(code_language, JudgeVersion.V202510) == object_file_path
    assert get_run_command(code_language, JudgeVersion.V202510) == run_command


@pytest.mark.parametrize(
    ("code_language", "judge_version", "expected_error"),
    [
        pytest.param(
            CodeLanguage.CPP20,
            JudgeVersion.V201907,
            r"C\+\+20 is not supported in judge version 201907\.",
            id="cpp20-v201907",
        ),
        pytest.param(
            CodeLanguage.CPP23,
            JudgeVersion.V201907,
            r"C\+\+23 is not supported in judge version 201907\.",
            id="cpp23-v201907",
        ),
        pytest.param(
            CodeLanguage.CPP17,
            JudgeVersion.V202510,
            r"C\+\+17 is not supported in judge version 202510\.",
            id="cpp17-v202510",
        ),
        pytest.param(
            CodeLanguage.CPP20,
            JudgeVersion.V202510,
            r"C\+\+20 is not supported in judge version 202510\.",
            id="cpp20-v202510",
        ),
        pytest.param(
            CodeLanguage.BASH,
            JudgeVersion.V202301,
            r"Bash is not supported in judge version 202301\.",
            id="bash-v202301",
        ),
        pytest.param(
            CodeLanguage.CSHARP,
            JudgeVersion.V202301,
            r"C# is not supported in judge version 202301\.",
            id="csharp-v202301",
        ),
        pytest.param(
            CodeLanguage.FISH,
            JudgeVersion.V202301,
            r"Fish is not supported in judge version 202301\.",
            id="fish-v202301",
        ),
        pytest.param(
            CodeLanguage.FORTRAN,
            JudgeVersion.V202301,
            r"Fortran is not supported in judge version 202301\.",
            id="fortran-v202301",
        ),
        pytest.param(
            CodeLanguage.GO,
            JudgeVersion.V202301,
            r"Go is not supported in judge version 202301\.",
            id="go-v202301",
        ),
        pytest.param(
            CodeLanguage.HASKELL,
            JudgeVersion.V202301,
            r"Haskell is not supported in judge version 202301\.",
            id="haskell-v202301",
        ),
        pytest.param(
            CodeLanguage.JAVASCRIPT,
            JudgeVersion.V202301,
            r"JavaScript is not supported in judge version 202301\.",
            id="javascript-v202301",
        ),
        pytest.param(
            CodeLanguage.JULIA,
            JudgeVersion.V202301,
            r"Julia is not supported in judge version 202301\.",
            id="julia-v202301",
        ),
        pytest.param(
            CodeLanguage.LEAN,
            JudgeVersion.V202301,
            r"Lean is not supported in judge version 202301\.",
            id="lean-v202301",
        ),
        pytest.param(
            CodeLanguage.OCAML,
            JudgeVersion.V202301,
            r"OCaml is not supported in judge version 202301\.",
            id="ocaml-v202301",
        ),
        pytest.param(
            CodeLanguage.PERL,
            JudgeVersion.V202301,
            r"Perl is not supported in judge version 202301\.",
            id="perl-v202301",
        ),
        pytest.param(
            CodeLanguage.PYPY,
            JudgeVersion.V202301,
            r"PyPy is not supported in judge version 202301\.",
            id="pypy-v202301",
        ),
        pytest.param(
            CodeLanguage.TYPESCRIPT,
            JudgeVersion.V202301,
            r"TypeScript is not supported in judge version 202301\.",
            id="typescript-v202301",
        ),
    ],
)
def test_unsupported_language_combination_raises(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        get_compile_command(code_language, judge_version)
    with pytest.raises(ValueError, match=expected_error):
        get_docker_image_name(code_language, judge_version)
