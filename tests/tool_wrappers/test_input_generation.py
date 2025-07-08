import tempfile
from contextlib import AbstractContextManager, nullcontext as does_not_raise
from pathlib import Path
from typing import Any

import pytest

import ale_bench.constants
from ale_bench.tool_wrappers.input_generation import (
    HostPathsGen,
    build_gen_command,
    get_gen_volumes,
    setup_paths_gen,
)


def test_setup_paths_gen() -> None:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        gen_host_paths = setup_paths_gen(temp_dir, [0, 1, 2])
        assert gen_host_paths.seeds_file.is_file()
        assert gen_host_paths.seeds_file.read_text() == "0\n1\n2\n"
        assert gen_host_paths.input_dir.is_dir()


def test_get_gen_volumes() -> None:
    gen_host_paths = HostPathsGen(seeds_file=Path("/tmp/test/seeds.txt"), input_dir=Path("/tmp/test/input"))
    gen_volumes = get_gen_volumes(gen_host_paths, Path("/tmp/test"))
    assert gen_volumes.keys() == {"/tmp/test/seeds.txt", "/tmp/test/input", "/tmp/test/tools/target/release/gen"}
    assert gen_volumes["/tmp/test/seeds.txt"]["bind"] == ale_bench.constants.SEEDS_FILE
    assert gen_volumes["/tmp/test/seeds.txt"]["mode"] == "ro"
    assert gen_volumes["/tmp/test/input"]["bind"] == ale_bench.constants.IN_DIR
    assert gen_volumes["/tmp/test/input"]["mode"] == "rw"
    assert gen_volumes["/tmp/test/tools/target/release/gen"]["bind"] == ale_bench.constants.GEN_BIN
    assert gen_volumes["/tmp/test/tools/target/release/gen"]["mode"] == "ro"


@pytest.mark.parametrize(
    "gen_kwargs,expected_context,expected_command",
    [
        pytest.param(
            {},
            does_not_raise(),
            f"{ale_bench.constants.GEN_BIN} {ale_bench.constants.SEEDS_FILE}",
            id="no_arguments",
        ),
        pytest.param(
            {"N": 30},
            does_not_raise(),
            f"{ale_bench.constants.GEN_BIN} --N=30 {ale_bench.constants.SEEDS_FILE}",
            id="with_keyword_argument",
        ),
        pytest.param(
            {"N": 30, "D": 2, "Q": 100},
            does_not_raise(),
            f"{ale_bench.constants.GEN_BIN} --N=30 --D=2 --Q=100 {ale_bench.constants.SEEDS_FILE}",
            id="with_multiple_keyword_arguments",
        ),
        pytest.param(
            {"N": 30, "D": 2, "Q": 100, "dir": "in2"},
            pytest.warns(UserWarning, match=r"`dir` is a reserved keyword and will be ignored\."),
            f"{ale_bench.constants.GEN_BIN} --N=30 --D=2 --Q=100 {ale_bench.constants.SEEDS_FILE}",
            id="with_multiple_keyword_arguments_with_dir",
        ),
    ],
)
def test_build_gen_command(
    gen_kwargs: dict[str, Any], expected_context: AbstractContextManager[None], expected_command: str
) -> None:
    with expected_context:
        assert build_gen_command(gen_kwargs) == expected_command
