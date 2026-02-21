"""Code language definitions and command helpers for ALE-Bench."""

from enum import Enum

import ale_bench.constants
from ale_bench.judge_command_profiles import (
    JUDGE_LANGUAGE_PROFILES,
    UNSUPPORTED_LANGUAGES_BY_JUDGE,
    JudgeLanguageProfile,
)


class CodeLanguage(str, Enum):
    """Enum for code languages."""

    BASH = "bash"
    CPP17 = "cpp17"
    CPP20 = "cpp20"
    CPP23 = "cpp23"
    CSHARP = "csharp"
    FISH = "fish"
    FORTRAN = "fortran"
    GO = "go"
    HASKELL = "haskell"
    JAVASCRIPT = "javascript"
    JULIA = "julia"
    LEAN = "lean"
    OCAML = "ocaml"
    PERL = "perl"
    PYPY = "pypy"
    PYTHON = "python"
    RUST = "rust"
    TYPESCRIPT = "typescript"
    # NOTE: Add more code languages here


class JudgeVersion(str, Enum):
    """Enum for judge versions."""

    V201907 = "201907"
    V202301 = "202301"
    V202510 = "202510"
    # NOTE: Add more judge versions here


LANGUAGE_DISPLAY_NAME: dict[CodeLanguage, str] = {
    CodeLanguage.BASH: "Bash",
    CodeLanguage.CPP17: "C++17",
    CodeLanguage.CPP20: "C++20",
    CodeLanguage.CPP23: "C++23",
    CodeLanguage.CSHARP: "C#",
    CodeLanguage.FISH: "Fish",
    CodeLanguage.FORTRAN: "Fortran",
    CodeLanguage.GO: "Go",
    CodeLanguage.HASKELL: "Haskell",
    CodeLanguage.JAVASCRIPT: "JavaScript",
    CodeLanguage.JULIA: "Julia",
    CodeLanguage.LEAN: "Lean",
    CodeLanguage.OCAML: "OCaml",
    CodeLanguage.PERL: "Perl",
    CodeLanguage.PYPY: "PyPy",
    CodeLanguage.PYTHON: "Python",
    CodeLanguage.RUST: "Rust",
    CodeLanguage.TYPESCRIPT: "TypeScript",
}


def _get_language_profile(code_language: CodeLanguage, judge_version: JudgeVersion) -> JudgeLanguageProfile:
    """Get command/file profile for a language and judge version."""
    profile_by_lang = JUDGE_LANGUAGE_PROFILES.get(judge_version.value)
    if profile_by_lang is None:
        msg = f"Unknown judge version: {judge_version.value}"
        raise ValueError(msg)
    if code_language.value not in profile_by_lang:
        if code_language.value in UNSUPPORTED_LANGUAGES_BY_JUDGE.get(judge_version.value, set()):
            msg = f"{LANGUAGE_DISPLAY_NAME[code_language]} is not supported in judge version {judge_version.value}."
            raise ValueError(msg)
        msg = f"Unknown code language or judge version: {code_language}, {judge_version}"
        raise ValueError(msg)
    return profile_by_lang[code_language.value]


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
    _get_language_profile(code_language, judge_version)
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
    return _get_language_profile(code_language, judge_version).compile_command


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
    return _get_language_profile(code_language, judge_version).run_command


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
    return _get_language_profile(code_language, judge_version).submission_file_path


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
    return _get_language_profile(code_language, judge_version).object_file_path
