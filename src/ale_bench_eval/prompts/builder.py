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
    BUDGET_ACTION_MATCH,
    BUDGET_ACTION_PROMPT,
    CODE_BLOCK_MATCH,
    CODE_BLOCK_STRING,
    CONSIDERATION_PROMPT,
    DIAGNOSTIC_FEEDBACK_PROMPT,
    EVOLUTION_CROSSOVER_PROMPT,
    EVOLUTION_MUTATION_PROMPT,
    FEEDBACK_PROMPT,
    IMPLEMENTATION_ANY_PROMPT,
    IMPLEMENTATION_SPECIFIC_PROMPT,
    NO_CODE_BLOCK_ANY_PROMPT,
    NO_CODE_BLOCK_SPECIFIC_PROMPT,
    PROBLEM_HEADER_PROMPT,
    REFINE_ANY_PROMPT,
    REFINE_SPECIFIC_PROMPT,
    SYSTEM_PROMPT,
    VIS_FEEDBACK_PROMPT,
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


def refine_instruction(args: PromptArgs) -> str:
    if args.code_language == "any":
        return REFINE_ANY_PROMPT[args.prompt_language].substitute(
            code_blocks=get_code_block_string_any(args.judge_version),
        )
    return REFINE_SPECIFIC_PROMPT[args.prompt_language].substitute(
        code_block=CODE_BLOCK_STRING[args.code_language],
    )


def diagnostic_feedback(args: PromptArgs, result: Result, worst_indices: list[int]) -> str:
    worst_set = set(worst_indices)
    case_lines = []
    for idx, case_result in enumerate(result.case_results):
        params = case_result.input_str.split("\n", 1)[0].strip() if case_result.input_str else "N/A"
        line = f'- Case {idx + 1}: params="{params}", score={case_result.absolute_score}'
        if case_result.judge_result != JudgeResult.ACCEPTED:
            line += f", judge={case_result.judge_result.value}"
        if idx in worst_set:
            line += " (WORST)"
        case_lines.append(line)
    return DIAGNOSTIC_FEEDBACK_PROMPT[args.prompt_language].substitute(case_table="\n".join(case_lines))


def create_feedback_message(
    args: PromptArgs,
    public_result: Result | None,
    *,
    diagnostic: str | None = None,
    visualizations: list[BinaryContent] | None = None,
    visualized_case_indices: list[int] | None = None,
) -> list[str | BinaryContent]:
    feedback = result_feedback(args, public_result)
    if diagnostic is not None:
        feedback += diagnostic
    refine_prompt = refine_instruction(args)
    feedback_prompt = FEEDBACK_PROMPT[args.prompt_language].substitute(feedback=feedback)
    if not visualizations:
        return [feedback_prompt + refine_prompt]
    case_indices = ", ".join(str(idx + 1) for idx in visualized_case_indices or [])
    feedback_prompt += VIS_FEEDBACK_PROMPT[args.prompt_language].substitute(case_indices=case_indices)
    return [feedback_prompt, *visualizations, refine_prompt]


def create_mutation_message(
    args: PromptArgs,
    problem: Problem,
    parent_code: str,
    parent_feedback: str,
    image_format: Literal["jpeg", "png", "webp"] = "png",
) -> list[str | BinaryContent]:
    contents = create_initial_message(args, problem, image_format)
    operator_prompt = EVOLUTION_MUTATION_PROMPT[args.prompt_language].substitute(
        parent_code=parent_code,
        parent_feedback=parent_feedback,
    )
    merged = merge_text_contents([*contents, operator_prompt + refine_instruction(args)])
    return convert_pillow_to_binary(merged, image_format)


def create_crossover_message(
    args: PromptArgs,
    problem: Problem,
    code_a: str,
    score_a: int,
    code_b: str,
    score_b: int,
    image_format: Literal["jpeg", "png", "webp"] = "png",
) -> list[str | BinaryContent]:
    contents = create_initial_message(args, problem, image_format)
    operator_prompt = EVOLUTION_CROSSOVER_PROMPT[args.prompt_language].substitute(
        code_a=code_a,
        score_a=score_a,
        code_b=code_b,
        score_b=score_b,
    )
    merged = merge_text_contents([*contents, operator_prompt + refine_instruction(args)])
    return convert_pillow_to_binary(merged, image_format)


def create_budget_action_message(
    args: PromptArgs,
    remaining_budget: int,
    history_rows: list[tuple[int, str, int]],
) -> str:
    history_table = "\n".join(f"- Attempt {index} ({action}): score={score}" for index, action, score in history_rows)
    return BUDGET_ACTION_PROMPT[args.prompt_language].substitute(
        remaining_budget=remaining_budget,
        history_table=history_table,
    )


def parse_budget_action(response: str) -> Literal["sample", "refine"]:
    """Parse the controller's action choice; the last match wins, and anything else means refine."""
    matches = BUDGET_ACTION_MATCH.findall(response)
    if not matches:
        return "refine"
    return "sample" if matches[-1].upper() == "SAMPLE" else "refine"


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
