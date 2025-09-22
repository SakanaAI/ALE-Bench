from typing import Any, Literal

import numpy as np

from ale_bench.data import ScoreType


def get_worst_score(score_type: ScoreType) -> int:
    return -1 if score_type == ScoreType.MAXIMIZE else 1000000000000000000


def select_solution_from_repeated_sampling(
    results_repeated_sampling: dict[int, dict[str, Any]],
    n_repeated_sampling: int,
    selection_method: Literal["best", "median"] = "median",
    score_type: ScoreType = ScoreType.MINIMIZE,
) -> tuple[str, str, int]:
    """
    Select a solution from repeated sampling results based on the specified method.

    Args:
        results_repeated_sampling: dictionary of sampling results indexed by iteration.
        n_repeated_sampling: Total number of repeated samplings performed.
        selection_method: Method to select solution - "best" or "median".
        score_type: Score type (MINIMIZE or MAXIMIZE).

    Returns:
        tuple of (selected_code_language, selected_code, selected_index)
    """
    if not results_repeated_sampling:
        raise ValueError("No results to select from")

    worst_score = get_worst_score(score_type)
    # Create sorted list of (index, score) tuples
    index_score_pairs = []

    for idx, result in results_repeated_sampling.items():
        if idx >= n_repeated_sampling:
            continue  # Ignore extra results beyond n_repeated_sampling
        score = result.get("overall_absolute_score", worst_score)
        index_score_pairs.append((idx, score))

    if not index_score_pairs:
        # Use the first solution if no valid scores found in results
        index_score_pairs = [(0, 0)]

    # Convert to numpy arrays for easier manipulation
    indices = np.array([p[0] for p in index_score_pairs])
    scores = np.array([p[1] for p in index_score_pairs])

    # Determine target index based on selection method
    if selection_method == "median":
        # Find the solution with score closest to median
        median_score = np.median(scores)
        distances = np.abs(scores - median_score)
        array_idx = np.argmin(distances)
    elif selection_method == "best":
        if score_type == ScoreType.MINIMIZE:
            array_idx = np.argmin(scores)
        elif score_type == ScoreType.MAXIMIZE:
            array_idx = np.argmax(scores)
    else:
        raise ValueError(f"Unknown selection method: {selection_method}")

    # Get the actual index in the original results dictionary
    target_index = indices[array_idx]

    # Return selected solution details
    target_result = results_repeated_sampling[target_index]
    target_code_language = target_result["code_language"]
    target_code = target_result["code"]

    return target_code_language, target_code, target_index


def select_solution_from_self_refine(
    results_self_refine: dict[int, dict[str, Any]],
    score_type: ScoreType = ScoreType.MINIMIZE,
    n_max_refine: int | None = None,
) -> tuple[str, str, int]:
    """
    Select a solution from self-refine results based on the specified method.
    Chose the best solution based on the absolute score.

    Args:
        results_self_refine: dictionary of self-refine results indexed by iteration.
        score_type: Score type (MINIMIZE or MAXIMIZE).
        n_max_refine: If specified, only consider the first n_max_refine results.

    Returns:
        tuple of (selected_code_language, selected_code, selected_index)
    """
    worst_score = get_worst_score(score_type)
    # Create sorted list of (index, score) tuples
    index_score_pairs = []

    for idx, result in results_self_refine.items():
        score = result.get("overall_absolute_score", worst_score)
        if n_max_refine is not None and idx >= n_max_refine:
            continue  # Ignore extra results beyond n_max_refine
        index_score_pairs.append((idx, score))

    if not index_score_pairs:
        # Use the first solution if no valid scores found in results
        index_score_pairs = [(0, 0)]

    # Convert to numpy arrays for easier manipulation
    indices = np.array([p[0] for p in index_score_pairs])
    scores = np.array([p[1] for p in index_score_pairs])

    if score_type == ScoreType.MINIMIZE:
        array_idx = np.argmin(scores)
    elif score_type == ScoreType.MAXIMIZE:
        array_idx = np.argmax(scores)

    # Get the actual index in the original results dictionary
    target_index = int(indices[array_idx])

    # Return selected solution details
    target_result = results_self_refine[target_index]
    target_code_language = target_result["code_language"]
    target_code = target_result["code"]

    return target_code_language, target_code, target_index
