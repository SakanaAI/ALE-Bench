from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("mcp.server.mcpserver", reason="Install ale-bench[mcp] to run the MCP tests")

from ale_bench_mcp import store as store_module
from ale_bench_mcp.store import SUMMARY_BYTES, ArtifactError, ArtifactStore


def test_capacity_evicts_details_but_keeps_summary(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, max_bytes=16384, max_records=10, retention_seconds=60)
    first = store.begin("session", "case_sets")
    store.finish(first, {"case_count": 1}, [("0-input", b"a" * 7000)])
    second = store.begin("session", "case_sets")
    store.finish(second, {"case_count": 1}, [("0-input", b"b" * 7000)])
    assert store.used_bytes <= 16384
    assert not store.describe(first)["details_available"]
    assert "evicted" in store.describe(first)["unavailable_reason"]
    assert store.describe(first)["case_count"] == 1
    with pytest.raises(ArtifactError, match="evicted"):
        store.read(first, "0-input")
    assert store.read(second, "0-input") == b"b" * 7000
    assert sum(path.stat().st_size for path in tmp_path.rglob("*") if path.is_file()) <= store.used_bytes


def test_oversized_result_is_not_partially_published(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, 16384, 10, 60)
    record = store.begin("session", "evaluations")
    result = store.finish(
        record, {"overall_absolute_score": 100}, [("0-input", b"a" * 7000), ("0-output", b"b" * 7000)]
    )
    assert result["overall_absolute_score"] == 100
    assert result["details_available"] is False
    assert not record.files
    assert store.used_bytes == SUMMARY_BYTES
    assert list(record.directory.iterdir()) == [record.directory / "summary.json"]


def test_expiry_is_not_extended_by_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = Mock(monotonic=Mock(return_value=100))
    monkeypatch.setattr(store_module, "time", clock)
    store = ArtifactStore(tmp_path, 16384, 10, 60)
    record = store.begin("session", "case_sets")
    store.finish(record, {"case_count": 1}, [("0-input", b"input")])
    clock.monotonic.return_value = 159
    store.get("session", record.identifier, "case_sets")
    clock.monotonic.return_value = 160
    with pytest.raises(ArtifactError, match="expired"):
        store.get("session", record.identifier, "case_sets")
    assert store.used_bytes == 0
    assert not record.directory.exists()


def test_record_limit_and_owner(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, 16384, 1, 60)
    record = store.begin("session", "case_sets")
    store.finish(record, {"case_count": 1}, [("0-input", b"input")])
    with pytest.raises(ArtifactError, match="does not belong"):
        store.get("different", record.identifier, "case_sets")
    new = store.begin("session", "case_sets")
    store.finish(new, {"case_count": 1}, [("0-input", b"new")])
    with pytest.raises(ArtifactError, match="index reached"):
        store.get("session", record.identifier, "case_sets")
    assert len(store.records) == len(store.removed) == 1


def test_disk_failure_preserves_completed_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = ArtifactStore(tmp_path, 16384, 10, 60)
    record = store.begin("session", "evaluations")
    original = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path.name == "0-output":
            original(path, data[:1])
            raise OSError
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    result = store.finish(record, {"overall_absolute_score": 100}, [("0-input", b"input"), ("0-output", b"output")])
    assert result["overall_absolute_score"] == 100
    assert result["details_available"] is False
    assert "storage_io_error" in result["unavailable_reason"]
    assert not (record.directory / "0-output").exists()
    assert not record.files
