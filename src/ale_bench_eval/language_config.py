from typing import Final, Literal, TypeAlias

from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.judge_command_profiles import JUDGE_LANGUAGE_PROFILES

EvalCodeLanguage: TypeAlias = Literal[
    "any",
    "bash",
    "cpp17",
    "cpp20",
    "cpp23",
    "csharp",
    "fish",
    "fortran",
    "go",
    "haskell",
    "javascript",
    "julia",
    "lean",
    "ocaml",
    "perl",
    "pypy",
    "python",
    "rust",
    "typescript",
]

StoredCodeLanguage: TypeAlias = Literal[""] | EvalCodeLanguage

EvalJudgeVersion: TypeAlias = Literal["201907", "202301", "202510"]

ALL_CODE_LANGUAGES: Final[tuple[str, ...]] = tuple(code_language.value for code_language in CodeLanguage)
ALL_CODE_LANGUAGES_SET: Final[set[str]] = set(ALL_CODE_LANGUAGES)
ALL_JUDGE_VERSIONS: Final[tuple[str, ...]] = tuple(judge_version.value for judge_version in JudgeVersion)
ALL_JUDGE_VERSIONS_SET: Final[set[str]] = set(ALL_JUDGE_VERSIONS)

SUPPORTED_LANGUAGES_BY_JUDGE_VERSION: Final[dict[str, list[str]]] = {
    judge_version.value: [
        code_language
        for code_language in ALL_CODE_LANGUAGES
        if code_language in JUDGE_LANGUAGE_PROFILES[judge_version.value]
    ]
    for judge_version in JudgeVersion
}

ANY_CODE_LANGUAGES_BY_JUDGE_VERSION: Final[dict[str, list[str]]] = {
    JudgeVersion.V201907.value: ["cpp17", "python", "rust"],
    JudgeVersion.V202301.value: ["cpp20", "python", "rust"],
    JudgeVersion.V202510.value: [
        "bash",
        "cpp23",
        "csharp",
        "fish",
        "fortran",
        "go",
        "haskell",
        "javascript",
        "julia",
        "lean",
        "ocaml",
        "perl",
        "pypy",
        "python",
        "rust",
        "typescript",
    ],
}


def validate_judge_version(judge_version: str) -> None:
    if judge_version not in ALL_JUDGE_VERSIONS_SET:
        msg = f"Invalid judge version: {judge_version}. Available options: {', '.join(ALL_JUDGE_VERSIONS)}"
        raise ValueError(msg)


def get_supported_languages(judge_version: str) -> list[str]:
    validate_judge_version(judge_version)
    return SUPPORTED_LANGUAGES_BY_JUDGE_VERSION[judge_version]


def get_any_languages(judge_version: str) -> list[str]:
    supported_languages = set(get_supported_languages(judge_version))
    return [
        language for language in ANY_CODE_LANGUAGES_BY_JUDGE_VERSION[judge_version] if language in supported_languages
    ]


def validate_code_language_for_judge(code_language: str, judge_version: str) -> None:
    validate_judge_version(judge_version)
    if code_language == "any":
        return
    if code_language not in ALL_CODE_LANGUAGES_SET:
        msg = f"Invalid code language: {code_language}. Available options: any, {', '.join(ALL_CODE_LANGUAGES)}"
        raise ValueError(msg)
    if code_language not in get_supported_languages(judge_version):
        msg = f"{code_language} is not supported in judge version {judge_version}."
        raise ValueError(msg)


def get_default_code_language(judge_version: str) -> str:
    if judge_version == JudgeVersion.V201907.value:
        return "cpp17"
    if judge_version == JudgeVersion.V202301.value:
        return "cpp20"
    if judge_version == JudgeVersion.V202510.value:
        return "cpp23"
    msg = f"Unsupported judge version: {judge_version}"
    raise ValueError(msg)
