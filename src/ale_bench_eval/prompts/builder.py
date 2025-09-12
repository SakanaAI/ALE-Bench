from io import BytesIO
from typing import Literal

from PIL import Image
from pydantic import BaseModel
from pydantic_ai import BinaryContent

from ale_bench.data import Problem
from ale_bench.result import CaseResult, JudgeResult, Result
from ale_bench.utils import parse_statement
from ale_bench_eval.prompts.texts import (
    ANY_CODE_LANGUAGES,
    CODE_BLOCK_MATCH,
    CODE_BLOCK_STRING,
    CODE_BLOCK_STRING_ANY,
    CODE_LANGUAGE_LIBRARIES,
    CODE_LANGUAGE_LIBRARIES_ANY,
    CODE_LANGUAGE_STRING,
    CODE_LANGUAGE_STRING_ANY,
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
)


class PromptArgs(BaseModel):
    code_language: Literal["any", "cpp17", "cpp20", "cpp23", "python", "rust"]
    prompt_language: Literal["en", "ja"]
    use_image: bool


def create_system_message(args: PromptArgs) -> str:
    return SYSTEM_PROMPT[args.prompt_language]


def merge_text_contents(
    contents: list[str | Image.Image | BinaryContent],
) -> list[str | Image.Image | BinaryContent]:
    merged_contents = []
    current_content: str | Image.Image | BinaryContent = contents[0]
    for content in contents[1:]:
        if isinstance(content, str):
            current_content += content  # type: ignore
        elif isinstance(content, (Image.Image, BinaryContent)):
            if current_content != "":
                merged_contents.append(current_content)
                current_content = ""
            merged_contents.append(content)
        else:
            raise ValueError(f"Invalid content type: {type(content)}")
    if current_content != "":
        merged_contents.append(current_content)
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
                language_strings=CODE_LANGUAGE_STRING_ANY,
                code_blocks=CODE_BLOCK_STRING_ANY,
                libraries=CODE_LANGUAGE_LIBRARIES_ANY,
            )
        )
    else:
        contents.append(
            IMPLEMENTATION_SPECIFIC_PROMPT[args.prompt_language].substitute(
                language=CODE_LANGUAGE_STRING[args.code_language],
                code_block=CODE_BLOCK_STRING[args.code_language],
                libraries=CODE_LANGUAGE_LIBRARIES[args.code_language],
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
            parse_statement(problem.statement, problem.statement_images)  # type: ignore
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
            language_strings=CODE_LANGUAGE_STRING_ANY,
            code_blocks=CODE_BLOCK_STRING_ANY,
        )
    else:
        return NO_CODE_BLOCK_SPECIFIC_PROMPT[args.prompt_language].substitute(
            language=CODE_LANGUAGE_STRING[args.code_language],
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
                code_blocks=CODE_BLOCK_STRING_ANY,
            )
        ]
    else:
        return [
            FEEDBACK_PROMPT[args.prompt_language].substitute(feedback=feedback)
            + REFINE_SPECIFIC_PROMPT[args.prompt_language].substitute(
                code_block=CODE_BLOCK_STRING[args.code_language],
            )
        ]


def get_code_from_response(response: str, code_language: str) -> tuple[str, str]:
    if code_language in CODE_BLOCK_MATCH:
        match = CODE_BLOCK_MATCH[code_language].findall(response)
        if len(match) > 0:
            return code_language, match[-1]  # Get the last code block
    elif code_language == "any":
        for lang, pattern in CODE_BLOCK_MATCH.items():
            if lang not in ANY_CODE_LANGUAGES:
                continue  # Skip unsupported languages
            match = pattern.findall(response)
            if len(match) > 0:
                return lang, match[-1]  # Get the last code block
    return "", ""
