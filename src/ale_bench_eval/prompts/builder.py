from io import BytesIO
from typing import Literal

from PIL import Image
from pydantic import BaseModel
from pydantic_ai import BinaryContent

from ale_bench.data import Problem
from ale_bench.result import CaseResult, JudgeResult, Result
from ale_bench.utils import parse_statement
from ale_bench_eval.language_config import EvalCodeLanguage, EvalJudgeVersion, get_any_languages
from ale_bench_eval.prompts.texts import (
    CODE_BLOCK_MATCH,
    CODE_BLOCK_STRING,
    CONSIDERATION_PROMPT,
    FEEDBACK_PROMPT,
    IMPLEMENTATION_ANY_PROMPT,
    IMPLEMENTATION_SPECIFIC_PROMPT,
    NO_CODE_BLOCK_ANY_PROMPT,
    NO_CODE_BLOCK_SPECIFIC_PROMPT,
    PROBLEM_HEADER_PROMPT,
    REFINE_ANY_PROMPT,
    REFINE_SPECIFIC_PROMPT,
    SYSTEM_PROMPT,
    get_code_block_string_any,
    get_code_language_libraries,
    get_code_language_libraries_any,
    get_code_language_string,
    get_code_language_string_any,
)


class PromptArgs(BaseModel):
    code_language: EvalCodeLanguage
    judge_version: EvalJudgeVersion
    prompt_language: Literal["en", "ja"]
    use_image: bool


def create_system_message(args: PromptArgs) -> str:
    return SYSTEM_PROMPT[args.prompt_language]


def merge_text_contents(
    contents: list[str | Image.Image | BinaryContent],
) -> list[str | Image.Image | BinaryContent]:
    merged_contents: list[str | Image.Image | BinaryContent] = []
    current_text = ""
    for content in contents:
        if isinstance(content, str):
            current_text += content
        elif isinstance(content, (Image.Image, BinaryContent)):
            if current_text:
                merged_contents.append(current_text)
                current_text = ""
            merged_contents.append(content)
        else:
            msg = f"Invalid content type: {type(content)}"
            raise TypeError(msg)
    if current_text:
        merged_contents.append(current_text)
    return merged_contents


def convert_pillow_to_binary(
    contents: list[str | Image.Image | BinaryContent],
    image_format: Literal["jpeg", "png", "webp"],
) -> list[str | BinaryContent]:
    converted_contents: list[str | BinaryContent] = []
    for content in contents:
        if isinstance(content, Image.Image):
            buffer = BytesIO()
            content.save(buffer, format=image_format)
            binary_content = BinaryContent(data=buffer.getvalue(), media_type=f"image/{image_format}")
            converted_contents.append(binary_content)
        else:
            converted_contents.append(content)
    return converted_contents


def create_initial_message(
    args: PromptArgs,
    problem: Problem,
    image_format: Literal["jpeg", "png", "webp"] = "png",
) -> list[str | BinaryContent]:
    contents: list[str | Image.Image | BinaryContent] = [CONSIDERATION_PROMPT[args.prompt_language]]
    if args.code_language == "any":
        contents.append(
            IMPLEMENTATION_ANY_PROMPT[args.prompt_language].substitute(
                language_strings=get_code_language_string_any(args.judge_version),
                code_blocks=get_code_block_string_any(args.judge_version),
                libraries=get_code_language_libraries_any(args.judge_version),
            )
        )
    else:
        contents.append(
            IMPLEMENTATION_SPECIFIC_PROMPT[args.prompt_language].substitute(
                language=get_code_language_string(args.code_language, args.judge_version),
                code_block=CODE_BLOCK_STRING[args.code_language],
                libraries=get_code_language_libraries(args.code_language, args.judge_version),
            )
        )
    contents.append(
        PROBLEM_HEADER_PROMPT[args.prompt_language].substitute(
            time_limit=problem.constraints.time_limit,
            memory_limit=problem.constraints.memory_limit // 1024 // 1024,
        )
    )
    if args.use_image:
        contents.extend(
            parse_statement(problem.statement, problem.statement_images)
            if args.prompt_language == "en"
            else parse_statement(problem.statement_ja, problem.statement_images)
        )
    else:
        contents.append(problem.statement if args.prompt_language == "en" else problem.statement_ja)
    initial_contents = merge_text_contents(contents)
    return convert_pillow_to_binary(initial_contents, image_format)


def no_code_block_message(args: PromptArgs) -> str:
    if args.code_language == "any":
        return NO_CODE_BLOCK_ANY_PROMPT[args.prompt_language].substitute(
            language_strings=get_code_language_string_any(args.judge_version),
            code_blocks=get_code_block_string_any(args.judge_version),
        )
    return NO_CODE_BLOCK_SPECIFIC_PROMPT[args.prompt_language].substitute(
        language=get_code_language_string(args.code_language, args.judge_version),
        code_block=CODE_BLOCK_STRING[args.code_language],
    )


def case_result_feedback(case_idx: int, case_result: CaseResult) -> str:
    return f"""- Case {case_idx}:
    Absolute score: {case_result.absolute_score}
    Execution time: {case_result.execution_time:.3f} sec
    Memory usage: {case_result.memory_usage // 1024 // 1024} MB
    Standard error: \"{case_result.error_str}\"
    Message: \"{case_result.message}\""""


def result_feedback(args: PromptArgs, result: Result | None) -> str:
    if result is None:
        return "No public result is available. Mainly because:\n" + no_code_block_message(args)
    feedback = f"[Public test result]\nOverall judge result: {result.overall_judge_result.value}\n"
    if result.overall_judge_result == JudgeResult.ACCEPTED:
        feedback += f"Overall absolute score: {result.overall_absolute_score}\n"
        feedback += "\n".join(
            [f"- Case {i}: {case_result.absolute_score}" for i, case_result in enumerate(result.case_results, 1)]
        )
    else:
        selected_case_idx = 0
        for idx, case_result in enumerate(result.case_results):
            if case_result.judge_result == result.overall_judge_result:
                selected_case_idx = idx
                break
        feedback += case_result_feedback(selected_case_idx + 1, result.case_results[selected_case_idx])
    return feedback


def create_feedback_message(args: PromptArgs, public_result: Result | None) -> list[str]:
    feedback = result_feedback(args, public_result)
    if args.code_language == "any":
        return [
            FEEDBACK_PROMPT[args.prompt_language].substitute(feedback=feedback)
            + REFINE_ANY_PROMPT[args.prompt_language].substitute(
                code_blocks=get_code_block_string_any(args.judge_version),
            )
        ]
    return [
        FEEDBACK_PROMPT[args.prompt_language].substitute(feedback=feedback)
        + REFINE_SPECIFIC_PROMPT[args.prompt_language].substitute(
            code_block=CODE_BLOCK_STRING[args.code_language],
        )
    ]


def get_code_from_response(response: str, code_language: str, judge_version: str) -> tuple[str, str]:
    if code_language in CODE_BLOCK_MATCH:
        match = CODE_BLOCK_MATCH[code_language].findall(response)
        if len(match) > 0:
            return code_language, match[-1]  # Get the last code block
    elif code_language == "any":
        for lang in get_any_languages(judge_version):
            pattern = CODE_BLOCK_MATCH.get(lang)
            if pattern is None:
                continue
            match = pattern.findall(response)
            if len(match) > 0:
                return lang, match[-1]  # Get the last code block
    return "", ""
