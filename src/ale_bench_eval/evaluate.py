from importlib.resources import files
from typing import Any

from ale_bench.result import ResourceUsage
from ale_bench.session import Session
from ale_bench_eval.data_types import EvaluationConfig, Solution
from ale_bench_eval.logger import SaveInfo


def get_ce_code(code_language: str) -> str:
    if code_language == "cpp17":
        return files("ale_bench_eval.codes").joinpath("ce_cpp17.cpp").read_text()
    if code_language == "cpp20":
        return files("ale_bench_eval.codes").joinpath("ce_cpp20.cpp").read_text()
    if code_language == "cpp23":
        return files("ale_bench_eval.codes").joinpath("ce_cpp23.cpp").read_text()
    elif code_language == "rust":
        return files("ale_bench_eval.codes").joinpath("ce_rust.rs").read_text()
    elif code_language == "python":
        return files("ale_bench_eval.codes").joinpath("ce_python.py").read_text()
    else:
        raise ValueError(f"Invalid code language: {code_language}")


def run_private_evaluation(
    config: EvaluationConfig,
    session: Session,
    solutions: list[Solution],
    save_info: SaveInfo | None = None,
) -> dict[str, Any]:
    """Run private evaluation on a list of solutions."""
    results_private = {}

    past_solution: Solution | None = None
    for solution in solutions:
        if save_info is not None:
            try:
                private_result = save_info.load_ale_bench_results(f"private_result_{solution.name}.json")
                final_rank, new_performance_rank, _ = session._standings.get_new_rank(private_result)
                final_performance = session._rank_performance_map.get_performance(new_performance_rank)
                results_private[solution.name] = {
                    "problem_id": config.problem_id,
                    "model_name": config.model_name,
                    "code_language": solution.code_language,
                    "code": solution.code,
                    "overall_absolute_score": private_result.overall_absolute_score,
                    "overall_relative_score": private_result.overall_relative_score,
                    "rank": final_rank,
                    "performance": final_performance,
                }
                save_info.logger.info(
                    f"Loaded cached private evaluation for {solution.name}: {private_result.overall_absolute_score}"
                )
                save_info.logger.info(
                    f"Private Evaluation ({solution.name}): {private_result.overall_absolute_score} "
                    f"Rank: {final_rank}, Performance: {final_performance}"
                )
                past_solution = solution
                continue
            except FileNotFoundError:
                pass

        if past_solution is not None and past_solution.code.strip() == solution.code.strip():
            # Skip evaluation if the code is the same as the past one
            results_private[solution.name] = results_private[past_solution.name]
            if save_info is not None:
                save_info.logger.info(
                    f"Skipping private evaluation for {solution.name} (same code as previous solution)"
                )
                save_info.logger.info(
                    f"Private Evaluation ({solution.name}): {results_private[solution.name]['overall_absolute_score']} "
                    f"Rank: {results_private[solution.name]['rank']}, "
                    f"Performance: {results_private[solution.name]['performance']}"
                )
                private_result = save_info.load_ale_bench_results(f"private_result_{past_solution.name}.json")
                save_info.save_ale_bench_results(f"private_result_{solution.name}.json", private_result)
            past_solution = solution
            continue

        try:
            if save_info is not None:
                save_info.logger.info(f"Running private evaluation for: {solution.name}")
            solution_code_language = solution.code_language
            solution_code = solution.code
            if solution_code.strip() == "":
                if solution_code_language == "any" or solution_code_language == "":
                    solution_code_language = "cpp20"  # default to cpp20
                solution_code = get_ce_code(solution_code_language)
            private_result, final_rank, final_performance = session.private_eval(
                solution_code, code_language=solution_code_language
            )

            if save_info is not None:
                save_info.logger.info(
                    f"Private Evaluation ({solution.name}): {private_result.overall_absolute_score} "
                    f"Rank: {final_rank}, Performance: {final_performance}"
                )
                save_info.save_ale_bench_results(f"private_result_{solution.name}.json", private_result)
            results_private[solution.name] = {
                "problem_id": config.problem_id,
                "model_name": config.model_name,
                "code_language": solution.code_language,
                "code": solution.code,
                "overall_absolute_score": private_result.overall_absolute_score,
                "overall_relative_score": private_result.overall_relative_score,
                "rank": final_rank,
                "performance": final_performance,
            }
        except Exception as e:
            if save_info is not None:
                save_info.logger.info(f"Private evaluation failed for {solution.name}: {e}")
            results_private[solution.name] = {
                "problem_id": config.problem_id,
                "model_name": config.model_name,
                "code_language": solution.code_language,
                "code": solution.code,
                "error": str(e),
                "overall_absolute_score": None,
                "overall_relative_score": None,
                "rank": None,
                "performance": None,
            }
        finally:
            past_solution = solution
            session._current_resource_usage = ResourceUsage(
                num_case_gen=session.current_resource_usage.num_case_gen,
                num_case_eval=session.current_resource_usage.num_case_eval,
                num_call_public_eval=session.current_resource_usage.num_call_public_eval,
                num_call_private_eval=0,
                execution_time_case_eval=session.current_resource_usage.execution_time_case_eval,
            )

    session.close()

    return results_private
