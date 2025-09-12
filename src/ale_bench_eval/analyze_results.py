import json
import statistics
from pathlib import Path
from typing import Any

import pandas as pd


def aggregate_results(execution_results: dict[str, dict[str, Any]], root_path: Path) -> dict[str, Any]:
    """
    Aggregate evaluation results across all problems to compute statistics.

    Args:
        execution_results: Results from parallel execution (success/failure status)
        root_path: Path to the results directory

    Returns:
        dictionary containing aggregated statistics for each evaluation method
    """
    print("📊 Aggregating results across all problems...")

    # Load experiment settings
    settings_path = root_path / "experiment_settings.json"
    experiment_settings = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                experiment_settings = json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load experiment settings: {e}")

    # Collect all final results
    problem_results = []
    cost_results_dict = {}
    successful_problems = []
    failed_problems = []

    for problem_id, status in execution_results.items():
        if not status["success"]:
            failed_problems.append(problem_id)
            continue

        final_results_path = root_path / problem_id / "results" / "final_results.json"
        if not final_results_path.exists():
            print(f"⚠️  Warning: Missing final_results.json for {problem_id}")
            failed_problems.append(problem_id)
            continue

        try:
            with open(final_results_path, "r") as f:
                result_data = json.load(f)
                result_data["problem_id"] = problem_id
                problem_results.append(result_data)
                successful_problems.append(problem_id)
        except Exception as e:
            print(f"❌ Error loading results for {problem_id}: {e}")
            failed_problems.append(problem_id)

        total_cost_path = root_path / problem_id / "results" / "total_cost.json"
        if not total_cost_path.exists():
            print(f"⚠️  Warning: Missing total_cost.json for {problem_id}")

        try:
            with open(total_cost_path, "r") as f:
                total_cost_data = json.load(f)
                cost_results_dict[problem_id] = total_cost_data
        except Exception as e:
            print(f"❌ Error loading total_cost.json for {problem_id}: {e}")

    if not problem_results:
        print("❌ No valid results found for aggregation")
        return {
            "error": "No valid results found",
            "experiment_settings": experiment_settings,
            "successful_problems": [],
            "failed_problems": failed_problems,
        }

    print(f"✅ Successfully loaded results for {len(successful_problems)} problems")
    if failed_problems:
        print(f"⚠️  Failed to load results for {len(failed_problems)} problems: {failed_problems}")

    # Initialize aggregation data structures
    method_data: dict[str, Any] = {}  # method_name -> {"ranks": [...], "performances": [...]}

    # Collect data by evaluation method
    for problem_result in problem_results:
        for method_name, method_result in problem_result.items():
            if method_name == "problem_id":
                continue

            if not isinstance(method_result, dict):
                continue

            # Extract rank and performance with null checks
            rank = method_result.get("rank")
            performance = method_result.get("performance")
            total_tokens = (
                cost_results_dict.get(problem_result["problem_id"], {}).get(method_name, {}).get("total_tokens", 0)
            )
            total_cost = (
                cost_results_dict.get(problem_result["problem_id"], {}).get(method_name, {}).get("total_cost", 0.0)
            )

            if method_name not in method_data:
                method_data[method_name] = {
                    "ranks": [],
                    "performances": [],
                    "total_tokens": [],
                    "total_cost": [],
                }

            # Only append valid numeric values
            if rank is not None and isinstance(rank, (int, float)):
                method_data[method_name]["ranks"].append(rank)
            if performance is not None and isinstance(performance, (int, float)):
                method_data[method_name]["performances"].append(performance)
            if total_tokens is not None and isinstance(total_tokens, (int, float)):
                method_data[method_name]["total_tokens"].append(total_tokens)
            if total_cost is not None and isinstance(total_cost, (int, float)):
                method_data[method_name]["total_cost"].append(total_cost)

    # Calculate statistics for each method
    aggregated_results = {
        "experiment_settings": experiment_settings,
        "evaluation_summary": {
            "total_problems": len(execution_results),
            "successful_problems": len(successful_problems),
            "failed_problems": len(failed_problems),
            "successful_problem_ids": successful_problems,
            "failed_problem_ids": failed_problems,
        },
        "method_statistics": {},
    }

    for method_name, data in method_data.items():
        ranks = data["ranks"]
        performances = data["performances"]

        method_stats = {
            "problem_count": len(successful_problems),
            "rank_statistics": _calculate_statistics(ranks),
            "performance_statistics": _calculate_statistics(performances),
            "total_tokens_statistics": _calculate_statistics(data["total_tokens"]),
            "total_cost_statistics": _calculate_statistics(data["total_cost"]),
        }

        aggregated_results["method_statistics"][method_name] = method_stats
    return aggregated_results


def _calculate_statistics(values: list[float]) -> dict[str, Any]:
    """Calculate comprehensive statistics for a list of values."""
    if not values:
        return {
            "count": 0,
            "values": [],
            "mean": None,
            "median": None,
            "std_dev": None,
            "min": None,
            "max": None,
            "total": None,
        }

    return {
        "count": len(values),
        "values": values,
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "total": sum(values),
    }


def display_aggregation_summary(aggregated_results: dict[str, Any]) -> str:
    """Generate a formatted summary of aggregated results as a string."""
    summary_text = ""

    # Change the output destination of all print functions to 's'
    summary_text += "\n" + "=" * 60 + "\n"
    summary_text += "📊 EVALUATION RESULTS SUMMARY\n"
    summary_text += "=" * 60 + "\n"

    # Check for errors
    if "error" in aggregated_results:
        summary_text += f"❌ Error: {aggregated_results['error']}\n"
        return summary_text  # If there is an error, return the current content

    # Display evaluation summary
    summary = aggregated_results.get("evaluation_summary", {})
    summary_text += f"🔍 Model: {aggregated_results['experiment_settings']['model_name']}\n"
    summary_text += f"📋 Total Problems: {summary.get('total_problems', 0)}\n"
    summary_text += f"✅ Successful: {summary.get('successful_problems', 0)}\n"
    summary_text += f"❌ Failed: {summary.get('failed_problems', 0)}\n"

    if summary.get("failed_problem_ids"):
        summary_text += f"   Failed problems: {', '.join(summary['failed_problem_ids'])}\n"

    # Display method statistics
    method_stats = aggregated_results.get("method_statistics", {})
    if method_stats:
        summary_text += "\n📈 METHOD PERFORMANCE:\n"
        summary_text += "-" * 60 + "\n"

        for method_name, stats in method_stats.items():
            summary_text += f"\n🔹 {method_name.upper().replace('_', ' ')}\n"

            # Rank statistics
            rank_stats = stats.get("rank_statistics", {})
            if rank_stats.get("count", 0) > 0:
                summary_text += f"   Rank - Mean: {rank_stats['mean']:.1f}, "
                summary_text += f"Median: {rank_stats['median']:.1f}, "
                summary_text += f"Std: {rank_stats['std_dev']:.1f}"
                summary_text += f"          Range: {rank_stats['min']:.0f} - {rank_stats['max']:.0f}\n"

            # Performance statistics
            perf_stats = stats.get("performance_statistics", {})
            if perf_stats.get("count", 0) > 0:
                summary_text += f"   Perf - Mean: {perf_stats['mean']:.3f}, "
                summary_text += f"Median: {perf_stats['median']:.3f}, "
                summary_text += f"Std: {perf_stats['std_dev']:.3f}"
                summary_text += f"          Range: {perf_stats['min']:.3f} - {perf_stats['max']:.3f}\n"

            # Total tokens statistics
            total_tokens_stats = stats.get("total_tokens_statistics", {})
            if total_tokens_stats.get("count", 0) > 0:
                summary_text += f"   Total Tokens: {total_tokens_stats['total']:.0f}\n"

            # Total cost statistics
            total_cost_stats = stats.get("total_cost_statistics", {})
            if total_cost_stats.get("count", 0) > 0:
                summary_text += f"   Total Cost: {total_cost_stats['total']:.4f}\n"

    # Display best method summary
    overall_summary = aggregated_results.get("summary", {})
    if overall_summary:
        summary_text += "\n🏆 BEST METHODS:\n"
        summary_text += "-" * 30 + "\n"
        if "best_method_by_average_rank" in overall_summary:
            summary_text += (
                f"🥇 Best Average Rank: {overall_summary['best_method_by_average_rank'].replace('_', ' ').title()}"
            )
        if "best_method_by_average_performance" in overall_summary:
            summary_text += (
                "🎯 Best Average Performance: "
                f"{overall_summary['best_method_by_average_performance'].replace('_', ' ').title()}"
            )

    summary_text += "\n" + "=" * 60 + "\n"

    print(summary_text)

    return summary_text


def make_result_table(aggregated_results: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Make the result table to pandas DataFrame."""
    result_table = {}
    # Display method statistics
    method_stats = aggregated_results.get("method_statistics", {})
    evaluation_summary = aggregated_results.get("evaluation_summary", {})
    successful_problem_ids = evaluation_summary.get("successful_problem_ids", [])

    if method_stats:
        for method_name, stats in method_stats.items():
            columns = [
                "rank_statistics",
                "performance_statistics",
                "total_tokens_statistics",
                "total_cost_statistics",
            ]
            table_dict = {}
            for col in columns:
                each_stats = stats.get(col, {})
                if each_stats.get("count", 0) > 0:
                    each_problem_results = each_stats.get("values")
                    table_dict[col.replace("_statistics", "")] = each_problem_results

            _df = pd.DataFrame(table_dict, index=successful_problem_ids)
            result_table[method_name] = _df
    return result_table


def estimate_total_cost(
    path_to_result: Path,
    selected_index: int | None = None,
    n_max_refine: int | None = None,
) -> tuple[float, float]:
    """Estimate the cost of the evaluation."""
    with open(path_to_result, "r") as f:
        result_json = json.load(f)

    total_tokens = 0
    total_cost = 0.0
    if selected_index is None:
        for i, result in result_json.items():
            if n_max_refine is not None and int(i) >= n_max_refine:
                continue
            _total_tokens = result.get("total_tokens", 0)
            _total_cost = result.get("cost", 0.0)
            total_tokens += _total_tokens if _total_tokens is not None else 0
            total_cost += _total_cost if _total_cost is not None else 0
    else:
        result = result_json[str(selected_index)]
        _total_tokens = result.get("total_tokens", 0)
        _total_cost = result.get("cost", 0.0)
        total_tokens += _total_tokens if _total_tokens is not None else 0
        total_cost += _total_cost if _total_cost is not None else 0
    return total_tokens, total_cost
