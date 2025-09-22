from collections.abc import Sequence
from typing import Any

from pydantic_ai.messages import ModelMessage, UserContent

from ale_bench.result import JudgeResult, Result
from ale_bench.session import Session
from ale_bench_eval.calc_cost import calc_cost
from ale_bench_eval.data_types import EvaluationConfig
from ale_bench_eval.evaluate import get_ce_code
from ale_bench_eval.logger import SaveInfo
from ale_bench_eval.prompts.builder import (
    create_feedback_message,
    get_code_from_response,
)
from ale_bench_eval.safe_generation import MaxTokenError, safe_generation
from ale_bench_eval.selection import get_worst_score

TIMEOUT_SECONDS = 1200
MAX_RETRIES = 30


def run_repeated_sampling(
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    user_prompt: str | Sequence[UserContent],
    system_prompt: str | Sequence[str],
    save_info: SaveInfo,
) -> dict[int, dict[str, Any]]:
    """Run repeated sampling to generate multiple solutions and find the best one."""
    public_cases = None
    if config.n_public_cases is not None:
        public_cases = session.case_gen(list(range(config.n_public_cases)))

    results_filename = "repeated_sampling_results.json"
    if (save_info.results / results_filename).exists():
        results_repeated_sampling_raw = save_info.load_results(results_filename)
        results_repeated_sampling = {int(k): v for k, v in results_repeated_sampling_raw.items()}
        save_info.logger.info(f"Loaded {len(results_repeated_sampling)} results from {results_filename}")
    else:
        results_repeated_sampling = {}
        save_info.logger.info(f"No results found for {results_filename}, starting from scratch")

    missing_indices = [i for i in range(config.n_repeated_sampling) if i not in results_repeated_sampling]
    if len(missing_indices) == 0:
        save_info.logger.info(
            f"Skipping repeated sampling because already generated {config.n_repeated_sampling} results"
        )
        return results_repeated_sampling

    for i in missing_indices:
        save_info.logger.info(f"Repeated sampling {i + 1}/{config.n_repeated_sampling}")
        is_context_length_overflow = False
        try:
            response = safe_generation(
                model_config=model_config,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                timeout=TIMEOUT_SECONDS,
                num_retries=MAX_RETRIES,
            )
            code_language, code = get_code_from_response(response.output, config.prompt_args.code_language)
        # NOTE: We don't expect MaxTokenError here for repeated sampling
        # NOTE: The model should be able to handle the prompt at this point
        except Exception as e:
            save_info.logger.error(f"Error for repeated sampling {i}: {e}")
            continue  # skip this iteration and do not save results

        overall_absolute_score = get_worst_score(session.problem.metadata.score_type)
        if response is not None:
            try:
                # If code is empty, use a compile-error-inducing code to save the evaluation result
                is_code_language_empty, is_code_empty = False, False
                if code.strip() == "":
                    is_code_empty = True
                    if code_language == "":
                        is_code_language_empty = True
                        code_language = "cpp20"
                    code = get_ce_code(code_language)
                # Evaluate the code
                if public_cases is not None:
                    public_result = session.case_eval(public_cases, code, code_language, skip_local_visualization=True)
                else:
                    public_result = session.public_eval(code, code_language)
                overall_absolute_score = (
                    public_result.overall_absolute_score
                    if public_result.overall_judge_result == JudgeResult.ACCEPTED
                    else get_worst_score(session.problem.metadata.score_type)
                )
                save_info.logger.info(f"Overall absolute score: {overall_absolute_score}")
                save_info.save_ale_bench_results(f"repeated_sampling_results_{i}.json", public_result)
            except Exception as e:
                save_info.logger.info(f"Code evaluation failed for sample {i}: {e}")
            finally:
                # If code or code_language is empty, set them to originally empty values
                if is_code_empty:
                    code = ""
                    if is_code_language_empty:
                        code_language = ""

        results_repeated_sampling[i] = {
            "code_language": code_language,
            "code": code,
            "overall_absolute_score": overall_absolute_score,
            "is_context_length_overflow": is_context_length_overflow,
            "input_tokens": (
                int(response.usage().input_tokens) if response is not None and response.usage() is not None else None
            ),
            "output_tokens": (
                int(response.usage().output_tokens) if response is not None and response.usage() is not None else None
            ),
            "total_tokens": (
                int(response.usage().total_tokens) if response is not None and response.usage() is not None else None
            ),
            "cost": (
                calc_cost(response.usage(), model_config["model_name"])  # type: ignore
                if response is not None and response.usage() is not None
                else None
            ),
        }

        # Save intermediate results
        if response is not None:
            save_info.save_conversations(f"repeated_sampling_conversations_{i}.json", response)
        save_info.save_results(results_filename, {str(k): v for k, v in results_repeated_sampling.items()})

    # Check if we have any successful results
    if not results_repeated_sampling:
        raise RuntimeError("No successful repeated sampling results generated")

    return results_repeated_sampling


def run_self_refinement(
    config: EvaluationConfig,
    model_config: dict[str, Any],
    session: Session,
    initial_message_history: list[ModelMessage],
    initial_public_result: Result,
    initial_result: dict[str, Any],
    save_info: SaveInfo,
) -> dict[int, dict[str, Any]]:
    """Run self-refinement iterations to improve the best solution."""
    public_cases = None
    if config.n_public_cases is not None:
        public_cases = session.case_gen(list(range(config.n_public_cases)))

    public_result: Result | None = None
    results_filename = "self_refine_results.json"
    conversations_filename = "self_refine_conversations.json"
    if (save_info.results / results_filename).exists() and (save_info.conversations / conversations_filename).exists():
        results_self_refine_raw = save_info.load_results(results_filename)
        results_self_refine = {int(k): v for k, v in results_self_refine_raw.items()}
        max_result_index = max(results_self_refine.keys())
        if results_self_refine[max_result_index]["is_context_length_overflow"]:
            save_info.logger.info(
                f"Already found a context length overflow for self-refine {max_result_index}, returning the results"
            )
            return results_self_refine
        message_history = save_info.load_conversations(conversations_filename).all_messages()
        public_result = save_info.load_ale_bench_results(
            f"self_refine_results_{len(results_self_refine) - 1}.json"  # exclude the initial repeated sampling result
        )
        save_info.logger.info(f"Loaded {len(results_self_refine)} results from {results_filename}")
    else:
        save_info.logger.info(f"No results found for {results_filename}, starting from scratch")
        results_self_refine = {0: initial_result}
        message_history = initial_message_history
        public_result = initial_public_result

    initial_index = len(results_self_refine)
    if set(results_self_refine.keys()) != set(range(initial_index)):
        raise ValueError("Results keys must be continuous from 0 to n-1")
    if initial_index >= config.n_self_refine:
        if not (save_info.results / results_filename).exists():  # NOTE: n_self_refine=1
            save_info.save_results(results_filename, {str(k): v for k, v in results_self_refine.items()})
        save_info.logger.info(f"Skipping self-refinement because already generated {initial_index} results")
        return results_self_refine

    for i in range(initial_index, config.n_self_refine):
        save_info.logger.info(f"Self-refine {i + 1}/{config.n_self_refine}")
        is_context_length_overflow = False
        try:
            response = safe_generation(
                model_config=model_config,
                user_prompt=create_feedback_message(config.prompt_args, public_result)[0],
                message_history=message_history,  # including system prompt
                timeout=TIMEOUT_SECONDS,
                num_retries=MAX_RETRIES,
            )
            code_language, code = get_code_from_response(response.output, config.prompt_args.code_language)
        except MaxTokenError as e:
            save_info.logger.info(f"Context length overflow for self-refine {i}: {e}")
            response = None
            code_language = ""
            code = ""
            is_context_length_overflow = True
        except Exception as e:
            save_info.logger.info(f"Error for self-refine {i}: {e}")
            raise ValueError(f"Error during self-refinement {i}: {e}")

        overall_absolute_score = get_worst_score(session.problem.metadata.score_type)
        if response is not None:
            try:
                # If code is empty, use a compile-error-inducing code to save the evaluation result
                is_code_language_empty, is_code_empty = False, False
                if code.strip() == "":
                    is_code_empty = True
                    if code_language == "":
                        is_code_language_empty = True
                        code_language = "cpp20"
                    code = get_ce_code(code_language)
                # Evaluate the code
                if public_cases is not None:
                    public_result = session.case_eval(public_cases, code, code_language, skip_local_visualization=True)
                else:
                    public_result = session.public_eval(code, code_language)
                overall_absolute_score = (
                    public_result.overall_absolute_score
                    if public_result.overall_judge_result == JudgeResult.ACCEPTED
                    else get_worst_score(session.problem.metadata.score_type)
                )
                save_info.logger.info(f"Overall absolute score: {overall_absolute_score}")
                save_info.save_ale_bench_results(f"self_refine_results_{i}.json", public_result)
            except Exception as e:
                save_info.logger.info(f"Code evaluation failed for refinement {i}: {e}")
                public_result = None
            finally:
                # If code or code_language is empty, set them to originally empty values
                if is_code_empty:
                    public_result = None
                    code = ""
                    if is_code_language_empty:
                        code_language = ""

        results_self_refine[i] = {
            "code_language": code_language,
            "code": code,
            "overall_absolute_score": overall_absolute_score,
            "is_context_length_overflow": is_context_length_overflow,
            "input_tokens": (
                int(response.usage().input_tokens) if response is not None and response.usage() is not None else None
            ),
            "output_tokens": (
                int(response.usage().output_tokens) if response is not None and response.usage() is not None else None
            ),
            "total_tokens": (
                int(response.usage().total_tokens) if response is not None and response.usage() is not None else None
            ),
            "cost": (
                calc_cost(response.usage(), model_config["model_name"])  # type: ignore
                if response is not None and response.usage() is not None
                else None
            ),
        }

        # Save intermediate results
        if response is not None:
            save_info.save_conversations(conversations_filename, response)
        save_info.save_results(results_filename, {str(k): v for k, v in results_self_refine.items()})

        # End self refine if context length overflow
        if response is None:
            save_info.logger.info(f"Context length overflow for self-refine {i}, stopping self-refinement")
            break

        message_history = response.all_messages()

    # Check if we have any successful refinement results
    if not results_self_refine:
        raise RuntimeError("No successful self-refinement results generated")

    return results_self_refine
