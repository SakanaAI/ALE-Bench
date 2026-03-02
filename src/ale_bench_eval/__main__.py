import json
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal, cast

from fire import Fire
from psutil import cpu_count

from ale_bench.data import list_problem_ids
from ale_bench_eval.analyze_results import (
    aggregate_results,
    display_aggregation_summary,
    estimate_total_cost,
    make_result_table,
)
from ale_bench_eval.data_types import EvaluationConfig, Solution
from ale_bench_eval.evaluate import run_private_evaluation
from ale_bench_eval.language_config import EvalCodeLanguage, EvalJudgeVersion, validate_code_language_for_judge
from ale_bench_eval.logger import SaveInfo, get_now_utc, get_now_utc_string
from ale_bench_eval.prompts.builder import (
    PromptArgs,
    create_initial_message,
    create_system_message,
)
from ale_bench_eval.safe_ale_session import start_ale_bench_session
from ale_bench_eval.safe_generation import parse_model_config
from ale_bench_eval.scaffolds import run_repeated_sampling, run_self_refinement
from ale_bench_eval.selection import (
    select_solution_from_repeated_sampling,
    select_solution_from_self_refine,
)


def power_of_two_indices(n: int) -> list[int]:
    """Generate a list of power of two indices up to n."""
    indices = [2**i for i in range(n.bit_length()) if 2**i <= n]
    if n not in indices:
        indices.append(n)
    return indices


def evaluate_contest(
    prompt_args: PromptArgs,
    model_name: str,
    model_config: dict[str, Any],
    n_repeated_sampling: int,
    n_self_refine: int,
    problem_id: str,
    lite_version: bool,
    num_workers: int,
    n_public_cases: int | None = None,
    selection_method: Literal["best", "median"] = "median",
    root_path: Path | None = None,
) -> None:
    """Main evaluation function orchestrating the entire benchmarking process."""
    start_time = get_now_utc()

    # Create configuration object
    config = EvaluationConfig(
        model_name=model_name,
        n_repeated_sampling=n_repeated_sampling,
        n_self_refine=n_self_refine,
        num_workers=num_workers,
        n_public_cases=n_public_cases,
        prompt_args=prompt_args,
        problem_id=problem_id,
        lite_version=lite_version,
        root_path=root_path,
    )

    # Initialize session and logging
    session = start_ale_bench_session(
        problem_id=problem_id,
        lite_version=lite_version,
        num_workers=num_workers,
    )

    save_info = SaveInfo(model_name, problem_id, root_path)
    save_info.logger.info("Start evaluation for %s on %s", model_name, problem_id)

    # Phase 1: Repeated sampling
    results_repeated_sampling = run_repeated_sampling(
        config=config,
        model_config=model_config,
        session=session,
        user_prompt=create_initial_message(prompt_args, session.problem),
        system_prompt=create_system_message(prompt_args),
        save_info=save_info,
    )
    expected_keys = set(range(n_repeated_sampling))
    actual_keys = {int(k) for k in results_repeated_sampling if int(k) in expected_keys}
    if actual_keys < expected_keys:
        diff = ", ".join(map(str, sorted(expected_keys - actual_keys)))
        msg = f"Mismatch in repeated sampling results keys. Missing keys: {diff}"
        raise ValueError(msg)

    # Phase 2: Select the best solution
    score_type = session.problem.metadata.score_type
    (
        selected_code_language_repeated_sampling,
        selected_code_repeated_sampling,
        selected_index_repeated_sampling,
    ) = select_solution_from_repeated_sampling(
        results_repeated_sampling=results_repeated_sampling,
        n_repeated_sampling=n_repeated_sampling,
        selection_method=selection_method,
        score_type=score_type,
    )
    save_info.logger.info(
        "Selected solution index: %s using method: %s for repeated sampling",
        selected_index_repeated_sampling,
        selection_method,
    )

    # Phase 3: Self-refinement
    if results_repeated_sampling[selected_index_repeated_sampling]["is_context_length_overflow"]:
        msg = "Context length overflow occurred in the selected repeated sampling result."
        raise ValueError(msg)
    initial_conversations = save_info.load_conversations(
        f"repeated_sampling_conversations_{selected_index_repeated_sampling}.json"
    )
    initial_public_result = save_info.load_ale_bench_results(
        f"repeated_sampling_results_{selected_index_repeated_sampling}.json"
    )
    results_self_refine = run_self_refinement(
        config=config,
        model_config=model_config,
        session=session,
        initial_message_history=initial_conversations.all_messages(),
        initial_public_result=initial_public_result,
        initial_result=results_repeated_sampling[selected_index_repeated_sampling],
        save_info=save_info,
    )

    # Phase 4: Private evaluation
    solutions_to_evaluate = [
        Solution(
            name="repeated_sampling",
            code=selected_code_repeated_sampling,
            code_language=selected_code_language_repeated_sampling,
        ),
    ]
    self_refine_target_indices = power_of_two_indices(n_self_refine)
    for i in self_refine_target_indices:
        (
            selected_code_language_self_refine_at_i,
            selected_code_self_refine_at_i,
            selected_index_self_refine_at_i,
        ) = select_solution_from_self_refine(
            results_self_refine=results_self_refine,
            score_type=score_type,
            n_max_refine=i,
        )
        save_info.logger.info("Selected solution index: %s for self-refine at %s", selected_index_self_refine_at_i, i)
        solutions_to_evaluate.append(
            Solution(
                name=f"self_refine_{i}",
                code=selected_code_self_refine_at_i,
                code_language=selected_code_language_self_refine_at_i,
            ),
        )
    private_result = run_private_evaluation(config, session, solutions_to_evaluate, save_info)
    save_info.logger.info("Private evaluation done.")

    # Save the last successful private result (for backward compatibility)
    if private_result is not None:
        save_info.save_results("final_results.json", private_result)
        save_info.logger.info("Final results saved.")

    # Estimate the total cost
    save_info.logger.info("Estimating total cost...")
    repeated_sampling_total_tokens, repeated_sampling_total_cost = estimate_total_cost(
        save_info.results / "repeated_sampling_results.json",
        selected_index_repeated_sampling,
    )
    save_info.logger.info(
        "Repeated sampling total cost: %s, total tokens: %s",
        repeated_sampling_total_cost,
        repeated_sampling_total_tokens,
    )
    total_cost = {
        "repeated_sampling": {
            "total_tokens": repeated_sampling_total_tokens,
            "total_cost": repeated_sampling_total_cost,
        },
    }
    for i in self_refine_target_indices:
        self_refine_total_tokens, self_refine_total_cost = estimate_total_cost(
            save_info.results / "self_refine_results.json",
            n_max_refine=i,
        )
        save_info.logger.info(
            "Self-refine %s total cost: %s, total tokens: %s", i, self_refine_total_cost, self_refine_total_tokens
        )
        total_cost[f"self_refine_{i}"] = {
            "total_tokens": self_refine_total_tokens,
            "total_cost": self_refine_total_cost,
        }
    save_info.save_results("total_cost.json", total_cost)
    save_info.logger.info("Total cost saved.")

    # Close the session
    session.close()

    # Log the time taken
    end_time = get_now_utc()
    elapsed_time = (end_time - start_time).total_seconds()
    save_info.logger.info("Time taken: %.2f seconds", elapsed_time)

    with (save_info.results / "time_taken.txt").open("a") as f:
        f.write(f"{elapsed_time / 60:.2f} minutes\n")

    save_info.logger.info("End evaluation for %s on %s", model_name, problem_id)


def _run_evaluation_task(
    prompt_args: PromptArgs,
    model_name: str,
    model_config: dict[str, Any],
    n_repeated_sampling: int,
    n_self_refine: int,
    problem_id: str,
    lite_version: bool,
    num_workers: int,
    n_public_cases: int | None,
    selection_method: Literal["best", "median"],
    root_path: Path,
) -> tuple[str, bool, str]:
    """Wrapper function for parallel evaluation execution."""
    try:
        print(f"▶️  Started: {model_name} on {problem_id}")
        evaluate_contest(
            prompt_args=prompt_args,
            model_name=model_name,
            model_config=model_config,
            n_repeated_sampling=n_repeated_sampling,
            n_self_refine=n_self_refine,
            problem_id=problem_id,
            lite_version=lite_version,
            num_workers=num_workers,
            n_public_cases=n_public_cases,
            selection_method=selection_method,
            root_path=root_path,
        )
        print(f"✅ Completed: {model_name} on {problem_id}")
    except Exception as e:
        error_msg = f"Error evaluating {problem_id}: {e!s}"
        print(f"❌ Failed: {model_name} on {problem_id} - {error_msg}")
        return problem_id, False, error_msg
    else:
        return problem_id, True, "Success"


def main(
    model_config_path: str,
    n_repeated_sampling: int = 1,
    n_self_refine: int = 1,
    num_workers: int = 1,
    n_public_cases: int | None = None,
    code_language: EvalCodeLanguage = "cpp20",
    judge_version: EvalJudgeVersion = "202301",
    prompt_language: Literal["en", "ja"] = "en",
    max_parallel_problems: int = 1,
    problem_ids_type: Literal["all", "lite", "debug"] = "debug",
    selection_method: Literal["best", "median"] = "median",
    use_statement_image: bool = False,
    root_path: str | None = None,
    skip_llm_inference: bool = False,
) -> None:
    """Main entry point for running LLM benchmarking evaluation."""
    start_time = get_now_utc()

    # NOTE:
    # python-fire may parse numeric-looking CLI args (e.g. 202510) as int.
    # Normalize all enum-like CLI parameters to strings at the entry point.
    code_language = cast("EvalCodeLanguage", str(code_language).strip())
    judge_version = cast("EvalJudgeVersion", str(judge_version).strip())
    prompt_language = cast('Literal["en", "ja"]', str(prompt_language).strip())

    physical_cores = cpu_count(logical=False)
    if physical_cores is None:
        warnings.warn(
            "Could not determine the number of physical CPU cores. Proceeding without this check.", stacklevel=2
        )
    elif num_workers * max_parallel_problems > physical_cores:
        msg = (
            f"num_workers * max_parallel_problems ({num_workers * max_parallel_problems}) "
            f"exceeds available CPU cores ({physical_cores})"
        )
        raise ValueError(msg)

    validate_code_language_for_judge(code_language, judge_version)

    prompt_args = PromptArgs(
        code_language=code_language,
        judge_version=judge_version,
        prompt_language=prompt_language,
        use_image=use_statement_image,
    )

    model_config_file_path = Path(model_config_path)
    with model_config_file_path.open() as f:
        model_config = json.load(f)
    if not isinstance(model_config, dict):
        msg = f"Invalid model configuration format in {model_config_path}"
        raise TypeError(msg)
    model_config = parse_model_config(model_config)
    model_name = model_config_file_path.stem

    # Create timestamped results directory
    exp_root = Path.cwd() / f"results/{model_name}_{get_now_utc_string()}"
    if root_path is not None:
        exp_root = Path(root_path)
    exp_root.mkdir(parents=True, exist_ok=True)

    setting_path = exp_root / "experiment_settings.json"
    if setting_path.is_file():  # Load the existing experiment settings
        existing_settings = json.load(setting_path.open())
        if existing_settings["model_name"] != model_name:
            msg = "Experiment settings already exist with different model_name"
            raise ValueError(msg)
        if existing_settings["model_config"] != model_config:
            msg = "Experiment settings already exist with different model_config"
            raise ValueError(msg)
        if existing_settings["n_repeated_sampling"] != n_repeated_sampling:
            msg = "Experiment settings already exist with different n_repeated_sampling"
            raise ValueError(msg)
        # NOTE: skip n_self_refine check to allow resuming with different n_self_refine
        # NOTE: skip num_workers check to allow resuming with different num_workers
        if existing_settings["n_public_cases"] != n_public_cases:
            msg = "Experiment settings already exist with different n_public_cases"
            raise ValueError(msg)
        if existing_settings["code_language"] != code_language:
            msg = "Experiment settings already exist with different code_language"
            raise ValueError(msg)
        if existing_settings.get("judge_version", "202301") != judge_version:
            msg = "Experiment settings already exist with different judge_version"
            raise ValueError(msg)
        if existing_settings["prompt_language"] != prompt_language:
            msg = "Experiment settings already exist with different prompt_language"
            raise ValueError(msg)
        # NOTE: skip max_parallel_problems check to allow resuming with different max_parallel_problems
        if existing_settings["problem_ids_type"] != problem_ids_type:
            msg = "Experiment settings already exist with different problem_ids_type"
            raise ValueError(msg)
        if existing_settings["selection_method"] != selection_method:
            msg = "Experiment settings already exist with different selection_method"
            raise ValueError(msg)
    # Save (update) experiment settings
    with setting_path.open("w") as f:
        json.dump(
            {
                "model_name": model_name,
                "model_config": model_config,
                "n_repeated_sampling": n_repeated_sampling,
                "n_self_refine": n_self_refine,
                "num_workers": num_workers,
                "n_public_cases": n_public_cases,
                "code_language": code_language,
                "judge_version": judge_version,
                "prompt_language": prompt_language,
                "max_parallel_problems": max_parallel_problems,
                "problem_ids_type": problem_ids_type,
                "selection_method": selection_method,
            },
            f,
            indent=4,
        )

    # Get the problem ids to evaluate
    lite_version = problem_ids_type != "all"
    problem_ids = ["ahc027", "ahc039"] if problem_ids_type == "debug" else list_problem_ids(lite_version=lite_version)
    print(f"\n🚀 Starting parallel evaluation of {len(problem_ids)} problems...")
    print(
        f"📊 Model: {model_name}, Repeated Sampling: {n_repeated_sampling}, Self-Refine: {n_self_refine}, "
        f"Code Language: {code_language}, Judge Version: {judge_version}"
    )

    if skip_llm_inference:
        print(f"🔍 Skipping LLM inference and loading results from {exp_root}")
        result_json_path = exp_root / "results.json"
        if not result_json_path.exists():
            msg = f"Results file not found at {result_json_path}"
            raise FileNotFoundError(msg)
        with result_json_path.open() as f:
            results = json.load(f)
    else:
        # Evaluate on problems in parallel
        with ThreadPoolExecutor(max_workers=max_parallel_problems) as executor:
            future_to_problem = {
                executor.submit(
                    _run_evaluation_task,
                    prompt_args,
                    model_name,
                    model_config,
                    n_repeated_sampling,
                    n_self_refine,
                    problem_id,
                    lite_version,
                    num_workers,
                    n_public_cases,
                    selection_method,
                    exp_root,
                ): problem_id
                for problem_id in problem_ids
            }
            results = {}
            for future in as_completed(future_to_problem):
                problem_id, success, message = future.result()
                results[problem_id] = {"success": success, "message": message}

        # Summary report
        successful = sum(1 for r in results.values() if r["success"])
        total = len(results)
        print("\n📋 Evaluation Summary:")
        print(f"   ✅ Successful: {successful}/{total}")
        print(f"   📁 Results saved to: {exp_root}")
        if successful < total:
            print("   ⚠️  Some evaluations failed:")
            for problem_id, result in results.items():
                if not result["success"]:
                    print(f"      • {problem_id}: {result['message']}")
        else:
            print("   🎉 All evaluations completed successfully!")
        with (exp_root / "results.json").open("w") as f:
            json.dump(results, f)

    # Aggregate the final results to obtain comprehensive statistics
    aggregated_results = aggregate_results(results, exp_root)

    # Save aggregated results
    with (exp_root / "aggregated_results.json").open("w") as f:
        json.dump(aggregated_results, f, indent=4)

    # save result table
    result_table = make_result_table(aggregated_results)
    for method_name, df in result_table.items():
        df.to_csv(exp_root / f"{method_name}.csv")

    # Display summary statistics
    summary = display_aggregation_summary(aggregated_results)
    with (exp_root / "summary.txt").open("w") as f:
        f.write(summary)

    print(f"\n📁 All results saved to: {exp_root}")
    print(f"📋 Individual problem results: {exp_root}/*/results/")
    print(f"📊 Aggregated statistics: {exp_root}/aggregated_results.json")

    # Save overall time taken
    end_time = get_now_utc()
    elapsed_time_str = f"Overall time taken: {(end_time - start_time).total_seconds() / 60:.2f} minutes"
    with (exp_root / "time_taken.txt").open("w") as f:
        f.write(elapsed_time_str)
    print(elapsed_time_str)


if __name__ == "__main__":
    Fire(main)
