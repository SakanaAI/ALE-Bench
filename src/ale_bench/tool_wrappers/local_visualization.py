from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

import ale_bench.constants
from ale_bench.tool_wrappers.case_runner import (
    HostPathsVis,
    build_vis_command,
    get_vis_volumes,
    run_vis_container,
)
from ale_bench.utils import read_svg


def setup_local_visualization_paths(
    problem_id: str,
    case_idx: int,
    input_str: str,
    output_str: str,
    temp_dir: Path,
) -> HostPathsVis:
    """Set up the paths for local visualization.

    Args:
        problem_id (str): The ID of the problem.
        case_idx (int): The index of the case.
        input_str (str): The input string for the case.
        output_str (str): The output string for the case.
        temp_dir (Path): The temporary directory to store files.

    Returns:
        HostPathsVis: An object containing paths for visualization.
    """
    input_file_ext = ale_bench.constants.INPUT_FILE.split(".")[-1]
    input_file = temp_dir / f"{problem_id}_{case_idx:06d}_input.{input_file_ext}"
    input_file.touch()
    input_file.write_text(input_str)
    output_file_ext = ale_bench.constants.OUTPUT_FILE.split(".")[-1]
    output_file = temp_dir / f"{problem_id}_{case_idx:06d}_output.{output_file_ext}"
    output_file.touch()
    output_file.write_text(output_str)
    local_visualization_container = (
        ale_bench.constants.LOCAL_VIS_SVG
        if problem_id in ale_bench.constants.VIS_SVG_GENERATION
        else ale_bench.constants.LOCAL_VIS_HTML
    )
    local_visualization_ext = local_visualization_container.rsplit(".", 1)[1]
    local_visualization_file = temp_dir / f"{problem_id}_{case_idx:06d}_local_visualization.{local_visualization_ext}"
    local_visualization_file.touch()
    return HostPathsVis(
        input_file=input_file,
        output_file=output_file,
        local_visualization_file=local_visualization_file,
    )


def case_iter_func(
    problem_id: str, case_idx: int, input_str: str, output_str: str, temp_dir: Path, tool_dir: Path, vis_command: str
) -> Image.Image | None:
    host_paths_vis = setup_local_visualization_paths(problem_id, case_idx, input_str, output_str, temp_dir)
    vis_volumes = get_vis_volumes(host_paths_vis, tool_dir)
    run_vis_container(vis_command, vis_volumes)
    # Read the local visualization SVG or HTML
    svg_text = host_paths_vis.local_visualization_file.read_text()
    svg_text = svg_text.replace("\n", "").removeprefix("<html><body>").removesuffix("</body></html>")
    if svg_text == "":
        return None  # No visualization generated (maybe WRONG_ANSWER)
    return read_svg(svg_text)


def local_visualization(
    inputs: list[str],
    outputs: list[str],
    problem_id: str,
    tool_dir: Path,
    num_workers: int,
) -> list[Image.Image | None]:
    """Run the cases for the given inputs and code.

    Args:
        inputs (list[str]): The list of inputs.
        outputs (list[str]): The list of outputs.
        problem_id (str): The ID of the problem.
        tool_dir (Path): The directory of the tools.
        num_workers (int): The number of workers for running cases.

    Returns:
        list[Image.Image | None]: The list of local visualization images for each case.
            If a case fails, the corresponding entry will be None.
    """
    if problem_id in ale_bench.constants.NO_LOCAL_VIS:
        return [None for _ in range(len(inputs))]  # No local visualization for this problem
    # Temporary directory
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # Prepare for the run
        vis_command = build_vis_command()

        # Run the code and calculate the score in the Docker container
        local_visualizations: list[Image.Image | None] = []
        if len(inputs) == 1 or num_workers == 1:
            for case_idx, (input_str, output_str) in enumerate(zip(inputs, outputs)):
                local_visualization_image = case_iter_func(
                    problem_id,
                    case_idx,
                    input_str,
                    output_str,
                    temp_dir,
                    tool_dir,
                    vis_command,
                )
                # Add the result
                local_visualizations.append(local_visualization_image)
        else:
            local_visualizations = [None for _ in range(len(inputs))]
            # Use ThreadPoolExecutor to run the cases in parallel
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                future_to_case_idx = {}
                for case_idx, (input_str, output_str) in enumerate(zip(inputs, outputs)):
                    future = executor.submit(
                        case_iter_func,
                        problem_id,
                        case_idx,
                        input_str,
                        output_str,
                        temp_dir,
                        tool_dir,
                        vis_command,
                    )
                    future_to_case_idx[future] = case_idx
                for future in as_completed(future_to_case_idx):
                    case_idx = future_to_case_idx[future]
                    try:
                        local_visualization_image = future.result()
                    except Exception:
                        local_visualization_image = None
                    local_visualizations[case_idx] = local_visualization_image
    return local_visualizations
