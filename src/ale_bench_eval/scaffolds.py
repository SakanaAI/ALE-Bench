from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import BoundedSemaphore
from time import sleep
from typing import Any, TypeVar

from pydantic_ai.messages import ModelMessage, UserContent
from pydantic_ai.run import AgentRunResult

from ale_bench.result import JudgeResult, Result
from ale_bench.session import Session
from ale_bench_eval.calc_cost import calc_cost
from ale_bench_eval.data_types import EvaluationConfig
from ale_bench_eval.evaluate import get_ce_code
from ale_bench_eval.language_config import get_default_code_language
from ale_bench_eval.logger import SaveInfo
from ale_bench_eval.prompts.builder import (
    create_feedback_message,
    get_code_from_response,
)
from ale_bench_eval.safe_generation import MaxTokenError, safe_generation
from ale_bench_eval.selection import get_worst_score

TIMEOUT_SECONDS = 3600
MAX_RETRIES = 30
JUDGE_MAX_RETRIES = 3
JUDGE_RETRY_WAIT_SECONDS = 5.0

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
        )
    else:
        public_result = session.public_eval(
            code,
            code_language,
            judge_version=config.prompt_args.judge_version,
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
    initial_public_result: Result,
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
                user_prompt=create_feedback_message(config.prompt_args, public_result)[0],
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
            if eval_code.strip() == "":
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
