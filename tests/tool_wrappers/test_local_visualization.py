import tempfile
from pathlib import Path

import pytest

from ale_bench.tool_wrappers.local_visualization import setup_local_visualization_paths


@pytest.mark.parametrize(
    "problem_id,case_idx,input_str,output_str,input_file_name,output_file_name,local_visualization_file_name",
    [
        pytest.param(
            "ahc001",
            0,
            "dummy input",
            "dummy output",
            "ahc001_000000_input.txt",
            "ahc001_000000_output.txt",
            "ahc001_000000_local_visualization.html",
            id="ahc001-0",
        ),
        pytest.param(
            "ahc002",
            1,
            "dummy input 1",
            "dummy output 1",
            "ahc002_000001_input.txt",
            "ahc002_000001_output.txt",
            "ahc002_000001_local_visualization.svg",
            id="ahc002-1",
        ),
        pytest.param(
            "ahc003",
            10,
            "dummy input 10",
            "dummy output 10",
            "ahc003_000010_input.txt",
            "ahc003_000010_output.txt",
            "ahc003_000010_local_visualization.svg",
            id="ahc003-10",
        ),
        pytest.param(
            "ahc004",
            100,
            "dummy input 100",
            "dummy output 100",
            "ahc004_000100_input.txt",
            "ahc004_000100_output.txt",
            "ahc004_000100_local_visualization.svg",
            id="ahc004-100",
        ),
        pytest.param(
            "ahc005",
            999,
            "dummy input 999",
            "dummy output 999",
            "ahc005_000999_input.txt",
            "ahc005_000999_output.txt",
            "ahc005_000999_local_visualization.svg",
            id="ahc005-999",
        ),
        pytest.param(
            "future-contest-2022-qual",
            1000,
            "dummy input for future contest",
            "dummy output for future contest",
            "future-contest-2022-qual_001000_input.txt",
            "future-contest-2022-qual_001000_output.txt",
            "future-contest-2022-qual_001000_local_visualization.svg",
            id="future-contest-2022-qual-1000",
        ),
        pytest.param(
            "ahc007",
            9999,
            "dummy input 9999",
            "dummy output 9999",
            "ahc007_009999_input.txt",
            "ahc007_009999_output.txt",
            "ahc007_009999_local_visualization.svg",
            id="ahc007-9999",
        ),
        pytest.param(
            "ahc008",
            10000,
            "dummy input 10000",
            "dummy output 10000",
            "ahc008_010000_input.txt",
            "ahc008_010000_output.txt",
            "ahc008_010000_local_visualization.html",
            id="ahc008-10000",
        ),
        pytest.param(
            "toyota2023summer-final",
            99999,
            "dummy input for toyota 2023 summer final",
            "dummy output for toyota 2023 summer final",
            "toyota2023summer-final_099999_input.txt",
            "toyota2023summer-final_099999_output.txt",
            "toyota2023summer-final_099999_local_visualization.html",
            id="toyota2023summer-final-99999",
        ),
        pytest.param(
            "ahc044",
            100000,
            "dummy input 100000",
            "dummy output 100000",
            "ahc044_100000_input.txt",
            "ahc044_100000_output.txt",
            "ahc044_100000_local_visualization.html",
            id="ahc044-100000",
        ),
    ],
)
def test_setup_paths_vis(
    problem_id: str,
    case_idx: int,
    input_str: str,
    output_str: str,
    input_file_name: str,
    output_file_name: str,
    local_visualization_file_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        host_paths_vis = setup_local_visualization_paths(
            problem_id,
            case_idx,
            input_str,
            output_str,
            temp_dir,
        )
        assert host_paths_vis.input_file.is_file()
        assert host_paths_vis.input_file.name == input_file_name
        assert host_paths_vis.input_file.read_text() == input_str
        assert host_paths_vis.output_file.is_file()
        assert host_paths_vis.output_file.name == output_file_name
        assert host_paths_vis.output_file.read_text() == output_str
        assert host_paths_vis.local_visualization_file.name == local_visualization_file_name
        assert host_paths_vis.local_visualization_file.is_file()
        assert host_paths_vis.local_visualization_file.stat().st_size == 0
