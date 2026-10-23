import pytest
from pydantic import ValidationError

pytest.importorskip("mcp.server.mcpserver", reason="Install ale-bench[mcp] to run the MCP tests")

from ale_bench_mcp.config import ServerConfig


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ServerConfig.model_fields:
        monkeypatch.delenv(f"ALE_BENCH_MCP_{name.upper()}", raising=False)
    config = ServerConfig.from_env()
    assert config.reuse_containers is True
    assert config.max_sessions == 5
    assert config.num_workers == 10
    assert config.maximum_num_case_eval == 10**18
    assert config.session_duration_seconds is None
    with pytest.raises(ValidationError, match="frozen"):
        config.maximum_num_case_eval = 999  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("NUM_WORKERS", "0"),
        ("MAX_SESSIONS", "-1"),
        ("MAXIMUM_NUM_CASE_EVAL", "-1"),
        ("MAXIMUM_NUM_CASE_GEN", "1.5"),
        ("MAXIMUM_NUM_CALL_PUBLIC_EVAL", "-1"),
        ("MAXIMUM_EXECUTION_TIME_CASE_EVAL", "nan"),
        ("MAXIMUM_EXECUTION_TIME_CASE_EVAL", "inf"),
        ("SESSION_DURATION_SECONDS", "0"),
        ("SESSION_DURATION_SECONDS", "inf"),
        ("REUSE_CONTAINERS", "invalid"),
        ("MAX_STORAGE_BYTES", "0"),
        ("MAX_ARTIFACTS", "0"),
        ("RETENTION_SECONDS", "nan"),
        ("RETENTION_SECONDS", "0"),
        ("MAX_READ_BYTES", "0"),
        ("DEFAULT_READ_BYTES", "1048577"),
        ("MAX_PAGE_ITEMS", "0"),
    ],
)
def test_invalid_config(name: str, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"ALE_BENCH_MCP_{name}", value)
    with pytest.raises(ValidationError):
        ServerConfig.from_env()
