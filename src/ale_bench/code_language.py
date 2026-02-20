"""Code language definitions and command helpers for ALE-Bench."""

from enum import Enum

import ale_bench.constants


class CodeLanguage(str, Enum):
    """Enum for code languages."""

    PYTHON = "python"
    CPP17 = "cpp17"
    CPP20 = "cpp20"
    CPP23 = "cpp23"
    RUST = "rust"
    # NOTE: Add more code languages here


class JudgeVersion(str, Enum):
    """Enum for judge versions."""

    V201907 = "201907"
    V202301 = "202301"
    # NOTE: Add more judge versions here


def get_docker_image_name(code_language: CodeLanguage, judge_version: JudgeVersion) -> str:
    """Get the Docker image name for running the user code.

    Args:
        code_language (CodeLanguage): The code language of the user code.
        judge_version (JudgeVersion): The judge version to use.

    Returns:
        str: The Docker image name.

    Raises:
        ValueError: If the code language is not supported in the given judge version.

    """
    if (code_language in (CodeLanguage.CPP20, CodeLanguage.CPP23)) and judge_version == JudgeVersion.V201907:
        msg = f"`{code_language.value}` are not supported in judge version 201907."
        raise ValueError(msg)
    return f"{ale_bench.constants.DOCKER_HUB_REPO}:{code_language.value}-{judge_version.value}"


def get_compile_command(code_language: CodeLanguage, judge_version: JudgeVersion) -> str:
    """Get the compile command for the user code.

    Args:
        code_language (CodeLanguage): The code language of the user code.
        judge_version (JudgeVersion): The judge version to use.

    Returns:
        str: The compile command.

    Raises:
        ValueError: If the code language is not supported in the given judge version.

    """
    if code_language == CodeLanguage.CPP17:
        if judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
            return (
                "g++ -std=gnu++17 -Wall -Wextra -O2 -DONLINE_JUDGE "
                "-I/opt/boost/gcc/include -L/opt/boost/gcc/lib -I/opt/ac-library -o a.out Main.cpp"
            )
    elif code_language == CodeLanguage.CPP20:
        if judge_version == JudgeVersion.V201907:
            msg = "C++20 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return (
                "g++-12 -std=gnu++20 -O2 -DONLINE_JUDGE -DATCODER -Wall -Wextra -mtune=native "
                "-march=native -fconstexpr-depth=2147483647 -fconstexpr-loop-limit=2147483647 "
                "-fconstexpr-ops-limit=2147483647 -I/opt/ac-library -I/opt/boost/gcc/include "
                "-L/opt/boost/gcc/lib -o a.out Main.cpp -lgmpxx -lgmp -I/usr/include/eigen3"
            )
    elif code_language == CodeLanguage.CPP23:
        if judge_version == JudgeVersion.V201907:
            msg = "C++23 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return (
                "g++-12 -std=gnu++2b -O2 -DONLINE_JUDGE -DATCODER -Wall -Wextra -mtune=native "
                "-march=native -fconstexpr-depth=2147483647 -fconstexpr-loop-limit=2147483647 "
                "-fconstexpr-ops-limit=2147483647 -I/opt/ac-library -I/opt/boost/gcc/include "
                "-L/opt/boost/gcc/lib -o a.out Main.cpp -lgmpxx -lgmp -I/usr/include/eigen3"
            )
    elif code_language == CodeLanguage.PYTHON:
        if judge_version == JudgeVersion.V201907:
            # NOTE: we added `-m py_compile` to compile but it was not used in the original judge
            return "python3.8 -m py_compile Main.py; python3.8 Main.py ONLINE_JUDGE 2> /dev/null"
        if judge_version == JudgeVersion.V202301:
            return "python3.11 -m py_compile Main.py; python3.11 Main.py ONLINE_JUDGE 2> /dev/null"
    elif code_language == CodeLanguage.RUST:
        if judge_version == JudgeVersion.V201907:
            # NOTE: we added `RUST_BACKTRACE=0` but it was not used in the original judge (v201907)
            return "RUST_BACKTRACE=0 cargo build --release --offline --quiet"
        if judge_version == JudgeVersion.V202301:
            return "RUST_BACKTRACE=0 cargo build --release --quiet --offline"
    # NOTE: Add more code languages here
    msg = f"Unknown code language or judge version: {code_language}, {judge_version}"
    raise ValueError(msg)


def get_run_command(code_language: CodeLanguage, judge_version: JudgeVersion) -> str:
    """Get the run command for the user code.

    Args:
        code_language (CodeLanguage): The code language of the user code.
        judge_version (JudgeVersion): The judge version to use.

    Returns:
        str: The run command.

    Raises:
        ValueError: If the code language is not supported in the given judge version.

    """
    if code_language == CodeLanguage.CPP17:
        if judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
            return "./a.out"
    elif code_language == CodeLanguage.CPP20:
        if judge_version == JudgeVersion.V201907:
            msg = "C++20 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return "./a.out"
    elif code_language == CodeLanguage.CPP23:
        if judge_version == JudgeVersion.V201907:
            msg = "C++23 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return "./a.out"
    elif code_language == CodeLanguage.PYTHON:
        if judge_version == JudgeVersion.V201907:
            return "python3.8 Main.py"
        if judge_version == JudgeVersion.V202301:
            return "python3.11 Main.py"
    elif code_language == CodeLanguage.RUST and judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
        return "./target/release/main"
    # NOTE: Add more code languages here
    msg = f"Unknown code language or judge version: {code_language}, {judge_version}"
    raise ValueError(msg)


def get_submission_file_path(code_language: CodeLanguage, judge_version: JudgeVersion) -> str:
    """Get the file path for the user code.

    Args:
        code_language (CodeLanguage): The code language of the user code.
        judge_version (JudgeVersion): The judge version to use.

    Returns:
        str: The file path.

    Raises:
        ValueError: If the code language is not supported in the given judge version.

    """
    if code_language == CodeLanguage.CPP17:
        if judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
            return "Main.cpp"
    elif code_language == CodeLanguage.CPP20:
        if judge_version == JudgeVersion.V201907:
            msg = "C++20 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return "Main.cpp"
    elif code_language == CodeLanguage.CPP23:
        if judge_version == JudgeVersion.V201907:
            msg = "C++23 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return "Main.cpp"
    elif code_language == CodeLanguage.PYTHON:
        if judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
            return "Main.py"
    elif code_language == CodeLanguage.RUST and judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
        return "src/main.rs"
    # NOTE: Add more code languages here
    msg = f"Unknown code language or judge version: {code_language}, {judge_version}"
    raise ValueError(msg)


def get_object_file_path(code_language: CodeLanguage, judge_version: JudgeVersion) -> str:
    """Get the object file path for the user code.

    Args:
        code_language (CodeLanguage): The code language of the user code.
        judge_version (JudgeVersion): The judge version to use.

    Returns:
        str: The object file path.

    Raises:
        ValueError: If the code language is not supported in the given judge version.

    """
    if code_language == CodeLanguage.CPP17:
        if judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
            return "a.out"
    elif code_language == CodeLanguage.CPP20:
        if judge_version == JudgeVersion.V201907:
            msg = "C++20 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return "a.out"
    elif code_language == CodeLanguage.CPP23:
        if judge_version == JudgeVersion.V201907:
            msg = "C++23 is not supported in judge version 201907."
            raise ValueError(msg)
        if judge_version == JudgeVersion.V202301:
            return "a.out"
    elif code_language == CodeLanguage.PYTHON:
        if judge_version == JudgeVersion.V201907:
            return "__pycache__/Main.cpython-38.pyc"
        if judge_version == JudgeVersion.V202301:
            return "__pycache__/Main.cpython-311.pyc"
    elif code_language == CodeLanguage.RUST and judge_version in (JudgeVersion.V201907, JudgeVersion.V202301):
        return "target/release/main"
    # NOTE: Add more code languages here
    msg = f"Unknown code language or judge version: {code_language}, {judge_version}"
    raise ValueError(msg)
