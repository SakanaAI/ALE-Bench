from importlib.resources import files
from typing import Any

from ale_bench.result import ResourceUsage
from ale_bench.session import Session
from ale_bench_eval.data_types import EvaluationConfig, Solution
from ale_bench_eval.language_config import get_default_code_language
from ale_bench_eval.logger import SaveInfo

CE_CODE_FILE_BY_LANGUAGE = {
    "bash": "ce_bash.bash",
    "cpp17": "ce_cpp17.cpp",
    "cpp20": "ce_cpp20.cpp",
    "cpp23": "ce_cpp23.cpp",
    "csharp": "ce_csharp.cs",
    "fish": "ce_fish.fish",
    "fortran": "ce_fortran.f90",
    "go": "ce_go.go",
    "haskell": "ce_haskell.hs",
    "javascript": "ce_javascript.js",
    "julia": "ce_julia.jl",
    "lean": "ce_lean.lean",
    "ocaml": "ce_ocaml.ml",
    "perl": "ce_perl.pl",
    "pypy": "ce_pypy.py",
    "python": "ce_python.py",
    "rust": "ce_rust.rs",
    "typescript": "ce_typescript.ts",
}
GENERIC_CE_CODE = "this code intentionally fails"


def get_ce_code(code_language: str) -> str:
    ce_filename = CE_CODE_FILE_BY_LANGUAGE.get(code_language)
    if ce_filename is not None:
        return files("ale_bench_eval.codes").joinpath(ce_filename).read_text()
    return GENERIC_CE_CODE


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
                final_rank, final_performance, _ = session.estimate_rank_and_performance(private_result)
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
                    "Loaded cached private evaluation for %s: %s",
                    solution.name,
                    private_result.overall_absolute_score,
                )
                save_info.logger.info(
                    "Private Evaluation (%s): %s Rank: %s, Performance: %s",
                    solution.name,
                    private_result.overall_absolute_score,
                    final_rank,
                    final_performance,
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
                    "Skipping private evaluation for %s (same code as previous solution)",
                    solution.name,
                )
                save_info.logger.info(
                    "Private Evaluation (%s): %s Rank: %s, Performance: %s",
                    solution.name,
                    results_private[solution.name]["overall_absolute_score"],
                    results_private[solution.name]["rank"],
                    results_private[solution.name]["performance"],
                )
                private_result = save_info.load_ale_bench_results(f"private_result_{past_solution.name}.json")
                save_info.save_ale_bench_results(f"private_result_{solution.name}.json", private_result)
            past_solution = solution
            continue

        try:
            if save_info is not None:
                save_info.logger.info("Running private evaluation for: %s", solution.name)
            solution_code_language = solution.code_language
            solution_code = solution.code
            if solution_code.strip() == "":
                if solution_code_language in {"any", ""}:
                    solution_code_language = get_default_code_language(config.prompt_args.judge_version)
                solution_code = get_ce_code(solution_code_language)
            private_result, final_rank, final_performance = session.private_eval(
                solution_code,
                code_language=solution_code_language,
                judge_version=config.prompt_args.judge_version,
            )

            if save_info is not None:
                save_info.logger.info(
                    "Private Evaluation (%s): %s Rank: %s, Performance: %s",
                    solution.name,
                    private_result.overall_absolute_score,
                    final_rank,
                    final_performance,
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
                save_info.logger.info("Private evaluation failed for %s: %s", solution.name, e)
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
            session._current_resource_usage = ResourceUsage(  # noqa: SLF001
                num_case_gen=session.current_resource_usage.num_case_gen,
                num_case_eval=session.current_resource_usage.num_case_eval,
                num_call_public_eval=session.current_resource_usage.num_call_public_eval,
                num_call_private_eval=0,
                execution_time_case_eval=session.current_resource_usage.execution_time_case_eval,
            )

    session.close()

    return results_private
