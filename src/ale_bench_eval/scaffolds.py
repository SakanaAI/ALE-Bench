import random
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import BoundedSemaphore
from time import sleep
from typing import Any, TypeVar

from pydantic_ai import BinaryContent
from pydantic_ai.messages import ModelMessage, UserContent
from pydantic_ai.run import AgentRunResult

from ale_bench.constants import NO_LOCAL_VIS
from ale_bench.data import ScoreType
from ale_bench.result import JudgeResult, Result
from ale_bench.session import Session
from ale_bench_eval.calc_cost import calc_cost
from ale_bench_eval.data_types import EvaluationConfig
from ale_bench_eval.evaluate import get_ce_code
from ale_bench_eval.language_config import get_default_code_language
from ale_bench_eval.logger import SaveInfo
from ale_bench_eval.prompts.builder import (
    convert_pillow_to_binary,
    create_budget_action_message,
    create_crossover_message,
    create_feedback_message,
    create_initial_message,
    create_mutation_message,
    create_system_message,
    diagnostic_feedback,
    get_code_from_response,
    parse_budget_action,
    result_feedback,
)
from ale_bench_eval.safe_generation import MaxTokenError, safe_generation
from ale_bench_eval.selection import (
    get_worst_score,
    select_solution_from_self_refine,
    select_worst_case_indices,
)

TIMEOUT_SECONDS = 3600
MAX_RETRIES = 30
JUDGE_MAX_RETRIES = 3
JUDGE_RETRY_WAIT_SECONDS = 5.0
MIN_CROSSOVER_POPULATION = 2

T = TypeVar("T")


def _run_with_retries(
    operation_name: str,
    save_info: SaveInfo,
    operation: Callable[[], T],
    max_attempts: int = JUDGE_MAX_RETRIES,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as e:  # noqa: PERF203
            last_error = e
            if attempt == max_attempts:
                save_info.logger.info("%s failed after %s attempts: %s", operation_name, max_attempts, e)
                break
            save_info.logger.info(
                "%s failed on attempt %s/%s: %s. Retrying...",
                operation_name,
                attempt,
                max_attempts,
                e,
            )
            sleep(JUDGE_RETRY_WAIT_SECONDS)

    msg = f"{operation_name} failed after {max_attempts} attempts"
    raise RuntimeError(msg) from last_error


def _evaluate_public_result_once(
    *,
    config: EvaluationConfig,
    session: Session,
    public_cases: list[str] | str | None,
    code: str,
    code_language: str,
) -> Result:
    if public_cases is not None:
        public_result = session.case_eval(
            public_cases,
            code,
            code_language,
            judge_version=config.prompt_args.judge_version,
            skip_local_visualization=True,
            reuse_containers=config.reuse_containers,
        )
    else:
        public_result = session.public_eval(
            code,
            code_language,
            judge_version=config.prompt_args.judge_version,
            reuse_containers=config.reuse_containers,
        )
    if public_result.overall_judge_result == JudgeResult.INTERNAL_ERROR:
        msg = "Judge returned INTERNAL_ERROR."
        raise RuntimeError(msg)
    return public_result


def _evaluate_and_save_public_result(
    *,
    config: EvaluationConfig,
    session: Session,
    public_cases: list[str] | str | None,
    code: str,
    code_language: str,
    save_info: SaveInfo,
    filename: str,
) -> Result:
    public_result = _run_with_retries(
        "Judge evaluation",
        save_info,
        lambda: _evaluate_public_result_once(
            config=config,
            session=session,
            public_cases=public_cases,
            code=code,
            code_language=code_language,
        ),
    )
    _run_with_retries(
        "Judge result save",
        save_info,
        lambda: save_info.save_ale_bench_results(filename, public_result),
    )
    return public_result


def _render_worst_case_visualizations(
    session: Session,
    public_result: Result,
    worst_indices: list[int],
    save_info: SaveInfo,
) -> tuple[list[BinaryContent], list[int]]:
    """Render visualization images of the worst cases; failures degrade to no images."""
    if session.problem.metadata.problem_id in NO_LOCAL_VIS:
        return [], []
    candidate_indices: list[int] = []
    input_strs: list[str] = []
    output_strs: list[str] = []
    for idx in worst_indices:
        case_result = public_result.case_results[idx]
        if case_result.input_str is None or case_result.output_str is None:
            continue
        candidate_indices.append(idx)
        input_strs.append(case_result.input_str)
        output_strs.append(case_result.output_str)
    if not candidate_indices:
        return [], []
    try:
        images = session.local_visualization(input_strs, output_strs)
    except Exception as e:
        save_info.logger.info("Local visualization failed: %s", e)
        return [], []
    if not isinstance(images, list):  # scalar result for a single case
        images = [images]
    rendered_indices: list[int] = []
    rendered_images = []
    for idx, image in zip(candidate_indices, images, strict=True):
        if image is not None:
            rendered_indices.append(idx)
            rendered_images.append(image)
    binary_contents = [
        content for content in convert_pillow_to_binary(rendered_images, "png") if isinstance(content, BinaryContent)
    ]
    return binary_contents, rendered_indices


def _build_refinement_user_prompt(
    config: EvaluationConfig,
    session: Session,
    public_result: Result | None,
    save_info: SaveInfo,
) -> list[str | BinaryContent]:
    if public_result is None or not (config.feedback_diagnostic or config.feedback_visualization):
        return create_feedback_message(config.prompt_args, public_result)
    worst_indices = select_worst_case_indices(
        public_result.case_results,
        session.problem.metadata.score_type,
        config.n_feedback_worst_cases,
    )
    diagnostic = None
    if config.feedback_diagnostic:
        diagnostic = diagnostic_feedback(config.prompt_args, public_result, worst_indices)
    visualizations: list[BinaryContent] = []
    rendered_indices: list[int] = []
    if config.feedback_visualization:
        visualizations, rendered_indices = _render_worst_case_visualizations(
            session, public_result, worst_indices, save_info
        )
    return create_feedback_message(
        config.prompt_args,
        public_result,
        diagnostic=diagnostic,
        visualizations=visualizations,
        visualized_case_indices=rendered_indices,
    )


def _delete_previous_self_refine_conversation(save_info: SaveInfo, i: int) -> None:
    if i <= 0:
        return
    previous_conversation_path = save_info.conversations / f"self_refine_conversations_{i - 1}.json"
    try:
        previous_conversation_path.unlink(missing_ok=True)
    except Exception as e:
        save_info.logger.info(
            "Failed to delete previous self-refine conversation %s: %s",
            previous_conversation_path.name,
            e,
        )


def _generate_repeated_sampling(
    i: int,
    config: EvaluationConfig,
    model_config: dict[str, Any],
    user_prompt: str | Sequence[UserContent],
    system_prompt: str | Sequence[str],
    save_info: SaveInfo,
    llm_semaphore: BoundedSemaphore | None,
) -> tuple[int, AgentRunResult[str], str, str]:
    save_info.logger.info("Repeated sampling %s/%s", i + 1, config.n_repeated_sampling)
    response = safe_generation(
        model_config=model_config,
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        timeout=TIMEOUT_SECONDS,
        num_retries=MAX_RETRIES,
        llm_semaphore=llm_semaphore,
    )
    code_language, code = get_code_from_response(
        response.output,
        config.prompt_args.code_language,
        config.prompt_args.judge_version,
    )
    return i, response, code_language, code


def _save_repeated_sampling_result(
    *,
    i: int,
    response: AgentRunResult[str],
    code_language: str,
    code: str,
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    public_cases: list[str] | str | None,
    save_info: SaveInfo,
    results_repeated_sampling: dict[int, dict[str, Any]],
    results_filename: str,
) -> None:
    is_context_length_overflow = False
    eval_code_language = code_language
    eval_code = code
    if eval_code.strip() == "":
        if eval_code_language == "":
            eval_code_language = get_default_code_language(config.prompt_args.judge_version)
        eval_code = get_ce_code(eval_code_language)

    public_result = _evaluate_and_save_public_result(
        config=config,
        session=session,
        public_cases=public_cases,
        code=eval_code,
        code_language=eval_code_language,
        save_info=save_info,
        filename=f"repeated_sampling_results_{i}.json",
    )
    overall_absolute_score = (
        public_result.overall_absolute_score
        if public_result.overall_judge_result == JudgeResult.ACCEPTED
        else get_worst_score(session.problem.metadata.score_type)
    )
    save_info.logger.info("Overall absolute score: %s", overall_absolute_score)

    usage = response.usage
    result_entry = {
        "code_language": code_language,
        "code": code,
        "overall_absolute_score": overall_absolute_score,
        "is_context_length_overflow": is_context_length_overflow,
        "input_tokens": int(usage.input_tokens),
        "output_tokens": int(usage.output_tokens),
        "total_tokens": int(usage.total_tokens),
        "cost": calc_cost(usage, model_config["model_name"]),
    }

    _run_with_retries(
        "Repeated sampling conversation save",
        save_info,
        lambda: save_info.save_conversations(f"repeated_sampling_conversations_{i}.json", response),
    )
    updated_results = {**results_repeated_sampling, i: result_entry}
    _run_with_retries(
        "Repeated sampling summary save",
        save_info,
        lambda: save_info.save_results(results_filename, {str(k): v for k, v in sorted(updated_results.items())}),
    )
    results_repeated_sampling[i] = result_entry


def run_repeated_sampling(
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    user_prompt: str | Sequence[UserContent],
    system_prompt: str | Sequence[str],
    save_info: SaveInfo,
    llm_semaphore: BoundedSemaphore | None = None,
    max_repeated_sampling_workers: int | None = None,
) -> dict[int, dict[str, Any]]:
    """Run repeated sampling to generate multiple solutions and find the best one."""
    if max_repeated_sampling_workers is not None and max_repeated_sampling_workers < 1:
        msg = "max_repeated_sampling_workers must be at least 1"
        raise ValueError(msg)

    public_cases = None
    if config.n_public_cases is not None:
        public_cases = session.case_gen(list(range(config.n_public_cases)))

    results_filename = "repeated_sampling_results.json"
    if (save_info.results / results_filename).exists():
        results_repeated_sampling_raw = save_info.load_results(results_filename)
        results_repeated_sampling = dict(sorted((int(k), v) for k, v in results_repeated_sampling_raw.items()))
        save_info.logger.info("Loaded %s results from %s", len(results_repeated_sampling), results_filename)
    else:
        results_repeated_sampling = {}
        save_info.logger.info("No results found for %s, starting from scratch", results_filename)

    missing_indices = [i for i in range(config.n_repeated_sampling) if i not in results_repeated_sampling]
    if len(missing_indices) == 0:
        save_info.logger.info(
            "Skipping repeated sampling because already generated %s results",
            config.n_repeated_sampling,
        )
        return results_repeated_sampling

    max_workers = min(
        len(missing_indices),
        config.n_repeated_sampling if max_repeated_sampling_workers is None else max_repeated_sampling_workers,
    )
    if max_workers == 1:
        for i in missing_indices:
            try:
                sample_index, response, code_language, code = _generate_repeated_sampling(
                    i,
                    config,
                    model_config,
                    user_prompt,
                    system_prompt,
                    save_info,
                    llm_semaphore,
                )
            # NOTE: We don't expect MaxTokenError here for repeated sampling
            # NOTE: The model should be able to handle the prompt at this point
            except Exception:
                save_info.logger.exception("Error for repeated sampling %s", i)
                continue  # skip this iteration and do not save results
            try:
                _save_repeated_sampling_result(
                    i=sample_index,
                    response=response,
                    code_language=code_language,
                    code=code,
                    config=config,
                    model_config=model_config,
                    session=session,
                    public_cases=public_cases,
                    save_info=save_info,
                    results_repeated_sampling=results_repeated_sampling,
                    results_filename=results_filename,
                )
            except Exception:
                save_info.logger.exception("Judge/save failed for repeated sampling %s", sample_index)
                continue
    else:
        save_info.logger.info("Running repeated sampling with up to %s in-flight LLM calls", max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    _generate_repeated_sampling,
                    i,
                    config,
                    model_config,
                    user_prompt,
                    system_prompt,
                    save_info,
                    llm_semaphore,
                ): i
                for i in missing_indices
            }
            for future in as_completed(future_to_index):
                i = future_to_index[future]
                try:
                    i, response, code_language, code = future.result()
                # NOTE: We don't expect MaxTokenError here for repeated sampling
                # NOTE: The model should be able to handle the prompt at this point
                except Exception:
                    save_info.logger.exception("Error for repeated sampling %s", i)
                    continue  # skip this iteration and do not save results
                try:
                    _save_repeated_sampling_result(
                        i=i,
                        response=response,
                        code_language=code_language,
                        code=code,
                        config=config,
                        model_config=model_config,
                        session=session,
                        public_cases=public_cases,
                        save_info=save_info,
                        results_repeated_sampling=results_repeated_sampling,
                        results_filename=results_filename,
                    )
                except Exception:
                    save_info.logger.exception("Judge/save failed for repeated sampling %s", i)
                    continue

    # Check if we have any successful results
    if not results_repeated_sampling:
        msg = "No successful repeated sampling results generated"
        raise RuntimeError(msg)

    return dict(sorted(results_repeated_sampling.items()))


def run_self_refinement(
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    initial_message_history: list[ModelMessage],
    initial_public_result: Result | None,
    initial_result: dict[str, Any],
    save_info: SaveInfo,
    llm_semaphore: BoundedSemaphore | None = None,
) -> dict[int, dict[str, Any]]:
    """Run self-refinement iterations to improve the best solution."""
    public_cases = None
    if config.n_public_cases is not None:
        public_cases = session.case_gen(list(range(config.n_public_cases)))

    public_result: Result | None = None
    results_filename = "self_refine_results.json"
    if (save_info.results / results_filename).exists():
        results_self_refine_raw = save_info.load_results(results_filename)
        results_self_refine = {int(k): v for k, v in results_self_refine_raw.items()}
        max_result_index = max(results_self_refine.keys())
        if results_self_refine[max_result_index]["is_context_length_overflow"]:
            save_info.logger.info(
                "Already found a context length overflow for self-refine %s, returning the results",
                max_result_index,
            )
            return results_self_refine
        if max_result_index == 0:
            message_history = initial_message_history
            public_result = initial_public_result
        else:
            conversations_filename = f"self_refine_conversations_{max_result_index}.json"
            message_history = save_info.load_conversations(conversations_filename).all_messages()
            if results_self_refine[max_result_index]["code"].strip() == "":
                public_result = None
            else:
                public_result = save_info.load_ale_bench_results(f"self_refine_results_{max_result_index}.json")
        save_info.logger.info("Loaded %s results from %s", len(results_self_refine), results_filename)
    else:
        save_info.logger.info("No results found for %s, starting from scratch", results_filename)
        results_self_refine = {0: initial_result}
        message_history = initial_message_history
        public_result = initial_public_result

    initial_index = len(results_self_refine)
    if set(results_self_refine.keys()) != set(range(initial_index)):
        msg = "Results keys must be continuous from 0 to n-1"
        raise ValueError(msg)
    if initial_index >= config.n_self_refine:
        if not (save_info.results / results_filename).exists():  # NOTE: n_self_refine=1
            _run_with_retries(
                "Self-refine summary save",
                save_info,
                lambda: save_info.save_results(results_filename, {str(k): v for k, v in results_self_refine.items()}),
            )
        save_info.logger.info("Skipping self-refinement because already generated %s results", initial_index)
        return results_self_refine

    for i in range(initial_index, config.n_self_refine):
        save_info.logger.info("Self-refine %s/%s", i + 1, config.n_self_refine)
        is_context_length_overflow = False
        try:
            response = safe_generation(
                model_config=model_config,
                user_prompt=_build_refinement_user_prompt(config, session, public_result, save_info),
                message_history=message_history,  # including system prompt
                timeout=TIMEOUT_SECONDS,
                num_retries=MAX_RETRIES,
                llm_semaphore=llm_semaphore,
            )
            code_language, code = get_code_from_response(
                response.output,
                config.prompt_args.code_language,
                config.prompt_args.judge_version,
            )
        except MaxTokenError as e:
            save_info.logger.info("Context length overflow for self-refine %s: %s", i, e)
            response = None
            code_language = ""
            code = ""
            is_context_length_overflow = True
        except Exception as e:
            save_info.logger.info("Error for self-refine %s: %s", i, e)
            msg = f"Error during self-refinement {i}: {e}"
            raise ValueError(msg) from e

        overall_absolute_score = get_worst_score(session.problem.metadata.score_type)
        if response is not None:
            eval_code_language = code_language
            eval_code = code
            is_code_empty = eval_code.strip() == ""
            if is_code_empty:
                if eval_code_language == "":
                    eval_code_language = get_default_code_language(config.prompt_args.judge_version)
                eval_code = get_ce_code(eval_code_language)
            try:
                public_result = _evaluate_and_save_public_result(
                    config=config,
                    session=session,
                    public_cases=public_cases,
                    code=eval_code,
                    code_language=eval_code_language,
                    save_info=save_info,
                    filename=f"self_refine_results_{i}.json",
                )
                overall_absolute_score = (
                    public_result.overall_absolute_score
                    if public_result.overall_judge_result == JudgeResult.ACCEPTED
                    else get_worst_score(session.problem.metadata.score_type)
                )
                save_info.logger.info("Overall absolute score: %s", overall_absolute_score)
            except Exception as e:
                save_info.logger.info("Code evaluation failed for refinement %s after retries: %s", i, e)
                msg = f"Judge/save failed during self-refinement {i}: {e}"
                raise ValueError(msg) from e
            if is_code_empty:
                public_result = None

        usage = response.usage if response is not None else None
        result_entry = {
            "code_language": code_language,
            "code": code,
            "overall_absolute_score": overall_absolute_score,
            "is_context_length_overflow": is_context_length_overflow,
            "input_tokens": int(usage.input_tokens) if usage is not None else None,
            "output_tokens": int(usage.output_tokens) if usage is not None else None,
            "total_tokens": int(usage.total_tokens) if usage is not None else None,
            "cost": calc_cost(usage, model_config["model_name"]) if usage is not None else None,
        }

        # Save intermediate results
        if response is not None:
            _run_with_retries(
                "Self-refine conversation save",
                save_info,
                lambda i=i, response=response: save_info.save_conversations(
                    f"self_refine_conversations_{i}.json", response
                ),
            )
        updated_results = {**results_self_refine, i: result_entry}
        _run_with_retries(
            "Self-refine summary save",
            save_info,
            lambda updated_results=updated_results: save_info.save_results(
                results_filename, {str(k): v for k, v in updated_results.items()}
            ),
        )
        results_self_refine[i] = result_entry
        if response is not None:
            _delete_previous_self_refine_conversation(save_info, i)

        # End self refine if context length overflow
        if response is None:
            save_info.logger.info("Context length overflow for self-refine %s, stopping self-refinement", i)
            break

        message_history = response.all_messages()

    # Check if we have any successful refinement results
    if not results_self_refine:
        msg = "No successful self-refinement results generated"
        raise RuntimeError(msg)

    return results_self_refine


PopulationKey = tuple[str, int]


def _load_phase3_results(
    save_info: SaveInfo,
    results_filename: str,
    initial_result: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    """Load (or seed) a phase-3 results dict whose keys must be continuous from 0 to n-1."""
    if (save_info.results / results_filename).exists():
        results_raw = save_info.load_results(results_filename)
        results = {int(k): v for k, v in results_raw.items()}
        save_info.logger.info("Loaded %s results from %s", len(results), results_filename)
    else:
        save_info.logger.info("No results found for %s, starting from scratch", results_filename)
        results = {0: initial_result}
    if set(results.keys()) != set(range(len(results))):
        msg = "Results keys must be continuous from 0 to n-1"
        raise ValueError(msg)
    return results


def _save_phase3_step(
    *,
    step_name: str,
    i: int,
    response: AgentRunResult[str] | None,
    entry: dict[str, Any],
    results: dict[int, dict[str, Any]],
    results_filename: str,
    conversations_filename: str,
    save_info: SaveInfo,
) -> None:
    if response is not None:
        _run_with_retries(
            f"{step_name} conversation save",
            save_info,
            lambda: save_info.save_conversations(conversations_filename, response),
        )
    updated_results = {**results, i: entry}
    _run_with_retries(
        f"{step_name} summary save",
        save_info,
        lambda: save_info.save_results(results_filename, {str(k): v for k, v in sorted(updated_results.items())}),
    )
    results[i] = entry


def _finalize_generation_step(
    *,
    response: AgentRunResult[str] | None,
    code_language: str,
    code: str,
    is_context_length_overflow: bool,
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    public_cases: list[str] | str | None,
    save_info: SaveInfo,
    filename: str,
    extra_response: AgentRunResult[str] | None = None,
) -> tuple[dict[str, Any], Result | None]:
    """Evaluate a generated solution and build the standard result entry.

    Token usage and cost cover both `response` and `extra_response` (e.g. a controller call).
    """
    overall_absolute_score = get_worst_score(session.problem.metadata.score_type)
    public_result: Result | None = None
    if response is not None:
        eval_code_language = code_language
        eval_code = code
        is_code_empty = eval_code.strip() == ""
        if is_code_empty:
            if eval_code_language == "":
                eval_code_language = get_default_code_language(config.prompt_args.judge_version)
            eval_code = get_ce_code(eval_code_language)
        public_result = _evaluate_and_save_public_result(
            config=config,
            session=session,
            public_cases=public_cases,
            code=eval_code,
            code_language=eval_code_language,
            save_info=save_info,
            filename=filename,
        )
        overall_absolute_score = (
            public_result.overall_absolute_score
            if public_result.overall_judge_result == JudgeResult.ACCEPTED
            else get_worst_score(session.problem.metadata.score_type)
        )
        save_info.logger.info("Overall absolute score: %s", overall_absolute_score)
        if is_code_empty:
            public_result = None

    usages = [r.usage for r in (extra_response, response) if r is not None]
    entry = {
        "code_language": code_language,
        "code": code,
        "overall_absolute_score": overall_absolute_score,
        "is_context_length_overflow": is_context_length_overflow,
        "input_tokens": sum(int(usage.input_tokens) for usage in usages) if usages else None,
        "output_tokens": sum(int(usage.output_tokens) for usage in usages) if usages else None,
        "total_tokens": sum(int(usage.total_tokens) for usage in usages) if usages else None,
        "cost": sum(calc_cost(usage, model_config["model_name"]) for usage in usages) if usages else None,
    }
    return entry, public_result


def _truncate_population(
    entries: list[tuple[PopulationKey, dict[str, Any]]],
    size: int,
    score_type: ScoreType,
) -> list[tuple[PopulationKey, dict[str, Any]]]:
    """Keep the top-`size` non-empty solutions ordered from best to worst (deterministic)."""
    valid = [(key, entry) for key, entry in entries if str(entry.get("code", "")).strip() != ""]
    sign = -1 if score_type == ScoreType.MAXIMIZE else 1
    valid.sort(key=lambda item: (sign * item[1]["overall_absolute_score"], item[0]))
    return valid[:size]


def _pick_crossover_parents(
    population: list[tuple[PopulationKey, dict[str, Any]]],
) -> tuple[tuple[PopulationKey, dict[str, Any]], tuple[PopulationKey, dict[str, Any]]]:
    """Pair the best member with the member whose score differs from it the most."""
    best = population[0]
    best_score = best[1]["overall_absolute_score"]
    partner = max(population[1:], key=lambda item: abs(item[1]["overall_absolute_score"] - best_score))
    return best, partner


def _load_parent_feedback(
    config: EvaluationConfig,
    save_info: SaveInfo,
    key: PopulationKey,
    parent_entry: dict[str, Any],
) -> str:
    kind, index = key
    try:
        parent_result = save_info.load_ale_bench_results(f"{kind}_results_{index}.json")
    except Exception as e:
        save_info.logger.info("Failed to load parent result %s_%s: %s", kind, index, e)
        return f"Overall absolute score: {parent_entry['overall_absolute_score']}"
    return result_feedback(config.prompt_args, parent_result)


def run_evolutionary_search(
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    results_repeated_sampling: dict[int, dict[str, Any]],
    initial_result: dict[str, Any],
    save_info: SaveInfo,
    llm_semaphore: BoundedSemaphore | None = None,
) -> dict[int, dict[str, Any]]:
    """Run an evolutionary search over a population of solutions.

    The population is seeded with the repeated sampling results. Each iteration generates one
    child via LLM mutation (improve one parent with its feedback) or crossover (combine two
    score-diverse parents), evaluates it, and truncates the population by score. Operator and
    parent choices are deterministic per (evolution_seed, iteration), which makes resuming from
    saved results exact.
    """
    public_cases = None
    if config.n_public_cases is not None:
        public_cases = session.case_gen(list(range(config.n_public_cases)))

    results_filename = "evolution_results.json"
    results_evolution = _load_phase3_results(save_info, results_filename, initial_result)
    initial_index = len(results_evolution)
    if initial_index >= config.n_self_refine:
        if not (save_info.results / results_filename).exists():  # NOTE: n_self_refine=1
            _run_with_retries(
                "Evolution summary save",
                save_info,
                lambda: save_info.save_results(results_filename, {str(k): v for k, v in results_evolution.items()}),
            )
        save_info.logger.info("Skipping evolution because already generated %s results", initial_index)
        return results_evolution

    score_type = session.problem.metadata.score_type
    for i in range(initial_index, config.n_self_refine):
        save_info.logger.info("Evolution %s/%s", i + 1, config.n_self_refine)
        rng = random.Random(config.evolution_seed * 1_000_003 + i)  # noqa: S311 (not cryptographic)
        # NOTE: Evolution entry 0 duplicates the selected repeated sampling entry, so exclude it
        seed_entries = [(("repeated_sampling", j), entry) for j, entry in results_repeated_sampling.items()]
        child_entries = [(("evolution", j), entry) for j, entry in results_evolution.items() if j > 0]
        population = _truncate_population(seed_entries + child_entries, config.evolution_population_size, score_type)
        if not population:
            msg = "Evolution population is empty (no valid parent solutions)"
            raise RuntimeError(msg)

        use_crossover = len(population) >= MIN_CROSSOVER_POPULATION and rng.random() < config.evolution_crossover_prob
        if use_crossover:
            (key_a, parent_a), (key_b, parent_b) = _pick_crossover_parents(population)
            user_prompt = create_crossover_message(
                config.prompt_args,
                session.problem,
                parent_a["code"],
                parent_a["overall_absolute_score"],
                parent_b["code"],
                parent_b["overall_absolute_score"],
            )
            operation = "crossover"
            parents = [f"{key_a[0]}_{key_a[1]}", f"{key_b[0]}_{key_b[1]}"]
        else:
            parent_key, parent_entry = population[rng.randrange(len(population))]
            parent_feedback = _load_parent_feedback(config, save_info, parent_key, parent_entry)
            user_prompt = create_mutation_message(
                config.prompt_args,
                session.problem,
                parent_entry["code"],
                parent_feedback,
            )
            operation = "mutation"
            parents = [f"{parent_key[0]}_{parent_key[1]}"]
        save_info.logger.info("Evolution operation: %s on %s", operation, parents)

        is_context_length_overflow = False
        response: AgentRunResult[str] | None = None
        code_language = ""
        code = ""
        try:
            response = safe_generation(
                model_config=model_config,
                user_prompt=user_prompt,
                system_prompt=create_system_message(config.prompt_args),
                timeout=TIMEOUT_SECONDS,
                num_retries=MAX_RETRIES,
                llm_semaphore=llm_semaphore,
            )
            code_language, code = get_code_from_response(
                response.output,
                config.prompt_args.code_language,
                config.prompt_args.judge_version,
            )
        except MaxTokenError as e:
            # NOTE: Prompts are stateless and bounded, so this should be rare; skip this child
            save_info.logger.info("Context length overflow for evolution %s: %s", i, e)
            is_context_length_overflow = True
        except Exception as e:
            save_info.logger.info("Error for evolution %s: %s", i, e)
            msg = f"Error during evolution {i}: {e}"
            raise ValueError(msg) from e

        entry, _ = _finalize_generation_step(
            response=response,
            code_language=code_language,
            code=code,
            is_context_length_overflow=is_context_length_overflow,
            config=config,
            model_config=model_config,
            session=session,
            public_cases=public_cases,
            save_info=save_info,
            filename=f"evolution_results_{i}.json",
        )
        entry["operation"] = operation
        entry["parents"] = parents
        _save_phase3_step(
            step_name="Evolution",
            i=i,
            response=response,
            entry=entry,
            results=results_evolution,
            results_filename=results_filename,
            conversations_filename=f"evolution_conversations_{i}.json",
            save_info=save_info,
        )

    return results_evolution


def _load_budget_message_history(
    save_info: SaveInfo,
    index: int,
    initial_message_history: list[ModelMessage],
) -> list[ModelMessage]:
    if index == 0:
        return initial_message_history
    return save_info.load_conversations(f"budget_conversations_{index}.json").all_messages()


def _load_budget_public_result(
    save_info: SaveInfo,
    index: int,
    initial_public_result: Result | None,
    results: dict[int, dict[str, Any]],
) -> Result | None:
    if str(results[index].get("code", "")).strip() == "":
        return None
    if index == 0:
        return initial_public_result
    return save_info.load_ale_bench_results(f"budget_results_{index}.json")


def run_budget_aware(
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    initial_message_history: list[ModelMessage],
    initial_public_result: Result | None,
    initial_result: dict[str, Any],
    save_info: SaveInfo,
    llm_semaphore: BoundedSemaphore | None = None,
) -> dict[int, dict[str, Any]]:
    """Run a budget-aware strategy where the model chooses each step's action.

    Each step first asks the model (a compact controller call) to choose between SAMPLE
    (a fresh solution in a fresh context) and REFINE (continue improving the current best
    solution), given the remaining budget and the attempt history. A context length overflow
    on REFINE forces SAMPLE for the remaining steps; an overflow on SAMPLE stops the run.
    """
    public_cases = None
    if config.n_public_cases is not None:
        public_cases = session.case_gen(list(range(config.n_public_cases)))

    results_filename = "budget_results.json"
    results_budget = _load_phase3_results(save_info, results_filename, initial_result)
    max_result_index = max(results_budget.keys())
    last_entry = results_budget[max_result_index]
    if last_entry["is_context_length_overflow"] and last_entry.get("action") == "sample":
        save_info.logger.info(
            "Already found a context length overflow on sample for budget %s, returning the results",
            max_result_index,
        )
        return results_budget
    initial_index = len(results_budget)
    if initial_index >= config.n_self_refine:
        if not (save_info.results / results_filename).exists():  # NOTE: n_self_refine=1
            _run_with_retries(
                "Budget summary save",
                save_info,
                lambda: save_info.save_results(results_filename, {str(k): v for k, v in results_budget.items()}),
            )
        save_info.logger.info("Skipping budget-aware strategy because already generated %s results", initial_index)
        return results_budget

    score_type = session.problem.metadata.score_type
    force_sample = any(
        entry.get("action") == "refine" and entry["is_context_length_overflow"] for entry in results_budget.values()
    )
    for i in range(initial_index, config.n_self_refine):
        remaining_budget = config.n_self_refine - i
        controller_response: AgentRunResult[str] | None = None
        if force_sample:
            action = "sample"
            save_info.logger.info("Budget %s/%s: forcing sample after refine overflow", i + 1, config.n_self_refine)
        else:
            history_rows = [
                (j, str(results_budget[j].get("action", "initial")), int(results_budget[j]["overall_absolute_score"]))
                for j in sorted(results_budget)
            ]
            try:
                controller_response = safe_generation(
                    model_config=model_config,
                    user_prompt=create_budget_action_message(config.prompt_args, remaining_budget, history_rows),
                    system_prompt=create_system_message(config.prompt_args),
                    timeout=TIMEOUT_SECONDS,
                    num_retries=MAX_RETRIES,
                    llm_semaphore=llm_semaphore,
                )
                action = parse_budget_action(controller_response.output)
            except Exception as e:
                save_info.logger.info("Budget controller failed at step %s: %s. Defaulting to refine", i, e)
                action = "refine"
            save_info.logger.info("Budget %s/%s: action=%s", i + 1, config.n_self_refine, action)

        refined_from: int | None = None
        is_context_length_overflow = False
        response: AgentRunResult[str] | None = None
        code_language = ""
        code = ""
        try:
            if action == "sample":
                response = safe_generation(
                    model_config=model_config,
                    user_prompt=create_initial_message(config.prompt_args, session.problem),
                    system_prompt=create_system_message(config.prompt_args),
                    timeout=TIMEOUT_SECONDS,
                    num_retries=MAX_RETRIES,
                    llm_semaphore=llm_semaphore,
                )
            else:
                _, _, best_index = select_solution_from_self_refine(results_budget, score_type=score_type)
                refined_from = best_index
                best_public_result = _load_budget_public_result(
                    save_info, best_index, initial_public_result, results_budget
                )
                response = safe_generation(
                    model_config=model_config,
                    user_prompt=_build_refinement_user_prompt(config, session, best_public_result, save_info),
                    message_history=_load_budget_message_history(save_info, best_index, initial_message_history),
                    timeout=TIMEOUT_SECONDS,
                    num_retries=MAX_RETRIES,
                    llm_semaphore=llm_semaphore,
                )
            code_language, code = get_code_from_response(
                response.output,
                config.prompt_args.code_language,
                config.prompt_args.judge_version,
            )
        except MaxTokenError as e:
            save_info.logger.info("Context length overflow for budget %s (%s): %s", i, action, e)
            is_context_length_overflow = True
            if action == "refine":
                force_sample = True
        except Exception as e:
            save_info.logger.info("Error for budget %s: %s", i, e)
            msg = f"Error during budget-aware step {i}: {e}"
            raise ValueError(msg) from e

        entry, _ = _finalize_generation_step(
            response=response,
            code_language=code_language,
            code=code,
            is_context_length_overflow=is_context_length_overflow,
            config=config,
            model_config=model_config,
            session=session,
            public_cases=public_cases,
            save_info=save_info,
            filename=f"budget_results_{i}.json",
            extra_response=controller_response,
        )
        entry["action"] = action
        entry["refined_from"] = refined_from
        # NOTE: Keep all budget conversations because any past best may be refined later
        _save_phase3_step(
            step_name="Budget",
            i=i,
            response=response,
            entry=entry,
            results=results_budget,
            results_filename=results_filename,
            conversations_filename=f"budget_conversations_{i}.json",
            save_info=save_info,
        )

        # End the run if even a fresh context overflows
        if is_context_length_overflow and action == "sample":
            save_info.logger.info("Context length overflow on sample for budget %s, stopping", i)
            break

    return results_budget
