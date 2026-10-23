"""Bounded, process-local artifact storage, independent of the MCP transport."""

import json
import shutil
import time
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

SUMMARY_BYTES = 4096
FILE_ENTRY_BYTES = 256


class ArtifactError(Exception):
    """An anticipated artifact access or capacity error."""


@dataclass
class Artifact:
    """Small in-memory index; case contents live only on disk."""

    identifier: str
    session_id: str
    kind: str
    directory: Path
    created_at: float
    summary: dict[str, Any] = field(default_factory=dict)
    files: dict[str, int] = field(default_factory=dict)
    unavailable_reason: str | None = None

    @property
    def size(self) -> int:
        """Account for detail bytes and a reserved summary allocation."""
        return SUMMARY_BYTES + sum(size + FILE_ENTRY_BYTES for size in self.files.values())


class ArtifactStore:
    """Keep bounded summaries and evict least-recently-read details under pressure."""

    def __init__(self, root: Path, max_bytes: int, max_records: int, retention_seconds: float) -> None:
        """Create a store in an exclusively owned directory."""
        self.root = root
        self.max_bytes = max_bytes
        self.max_records = max_records
        self.retention_seconds = retention_seconds
        self.records: OrderedDict[str, Artifact] = OrderedDict()
        self.removed: OrderedDict[str, str] = OrderedDict()

    @property
    def used_bytes(self) -> int:
        """Return accounted logical bytes, including summary reservations."""
        return sum(record.size for record in self.records.values())

    def _forget(self, identifier: str, reason: str) -> None:
        record = self.records.pop(identifier)
        shutil.rmtree(record.directory)
        self.removed[identifier] = reason
        while len(self.removed) > self.max_records:
            self.removed.popitem(last=False)

    def prune(self) -> None:
        """Remove expired artifacts on access; reads never extend their lifetime."""
        now = time.monotonic()
        for identifier, record in list(self.records.items()):
            if now - record.created_at >= self.retention_seconds:
                self._forget(identifier, "expired: the configured retention period elapsed")

    def _drop_details(self, record: Artifact, reason: str) -> None:
        for name in list(record.files):
            (record.directory / name).unlink(missing_ok=True)
            del record.files[name]
        record.unavailable_reason = reason

    def _make_room(self, size: int, exclude: str | None = None) -> bool:
        for record in self.records.values():
            if self.used_bytes + size <= self.max_bytes:
                return True
            if record.identifier != exclude and record.files:
                self._drop_details(record, "evicted: storage capacity was needed for newer artifacts")
        return self.used_bytes + size <= self.max_bytes

    def begin(self, session_id: str, kind: str) -> Artifact:
        """Reserve summary space before executing an operation that consumes budget."""
        self.prune()
        while len(self.records) >= self.max_records or not self._make_room(SUMMARY_BYTES):
            if not self.records:
                msg = "Storage capacity is too small for an operation summary; increase MAX_STORAGE_BYTES."
                raise ArtifactError(msg)
            self._forget(next(iter(self.records)), "evicted: the artifact index reached its capacity")
        identifier = uuid4().hex
        directory = self.root / identifier
        directory.mkdir()
        record = Artifact(identifier, session_id, kind, directory, time.monotonic())
        self.records[identifier] = record
        return record

    def discard(self, record: Artifact) -> None:
        """Release a reservation after an operation fails."""
        self._forget(record.identifier, "operation failed; no result was retained")

    def finish(self, record: Artifact, summary: dict[str, Any], files: Iterable[tuple[str, bytes]]) -> dict[str, Any]:
        """Store details, reporting storage failure without disguising a completed operation as a failed one."""
        record.summary = summary
        # Retention starts at completion, not before a potentially long evaluation.
        record.created_at = time.monotonic()
        try:
            encoded = json.dumps(summary, ensure_ascii=False).encode()
            if len(encoded) > SUMMARY_BYTES:
                msg = "Operation summary exceeded its reserved capacity."
                raise ArtifactError(msg)
            (record.directory / "summary.json").write_bytes(encoded)
            for name, data in files:
                if not self._make_room(len(data) + FILE_ENTRY_BYTES, exclude=record.identifier):
                    self._drop_details(record, "storage_limit: result details exceed MAX_STORAGE_BYTES")
                    break
                # Names are generated internally, never taken from a client URI.
                path = record.directory / name
                try:
                    path.write_bytes(data)
                except OSError:
                    path.unlink(missing_ok=True)
                    raise
                record.files[name] = len(data)
        except OSError:
            self._drop_details(record, "storage_io_error: details could not be written to artifact storage")
        return self.describe(record)

    def describe(self, record: Artifact) -> dict[str, Any]:
        """Return a bounded summary with the current detail availability."""
        return {
            **record.summary,
            "job_id": record.identifier,
            "id": record.session_id,
            "kind": record.kind,
            "details_available": record.unavailable_reason is None,
            "unavailable_reason": record.unavailable_reason,
            "expires_in_seconds": max(0, self.retention_seconds - (time.monotonic() - record.created_at)),
        }

    def get(self, session_id: str, identifier: str, kind: str) -> Artifact:
        """Resolve ownership and report expired, evicted, and unknown artifacts distinctly."""
        self.prune()
        record = self.records.get(identifier)
        if record is None:
            reason = self.removed.get(identifier, "unknown or no longer retained; check the ID and server lifetime")
            msg = f"Job {identifier}: {reason}. Evaluation/generation is not rerun by a read."
            raise ArtifactError(msg)
        if record.session_id != session_id:
            msg = f"Job {identifier} does not belong to session id={session_id}. Use the id that created this job."
            raise ArtifactError(msg)
        if record.kind != kind:
            msg = (
                f"Job {identifier} has kind={record.kind}; expected {kind}. "
                f"Read ale://sessions/{session_id}/{kind} for matching job_id values."
            )
            raise ArtifactError(msg)
        self.records.move_to_end(identifier)
        return record

    def read(self, record: Artifact, name: str, offset: int = 0, limit: int | None = None) -> bytes:
        """Read a known internal blob, optionally bounded by a byte range."""
        if record.unavailable_reason:
            msg = f"Artifact details unavailable ({record.unavailable_reason}); its summary is still readable."
            raise ArtifactError(msg)
        if name not in record.files:
            msg = "Resource is not available: unknown case/field, private data, or visualization not generated."
            raise ArtifactError(msg)
        with (record.directory / name).open("rb") as stream:
            stream.seek(offset)
            return stream.read(limit if limit is not None else -1)

    def add_image(self, record: Artifact, name: str, data: bytes) -> None:
        """Cache one image without removing the input/output details of its evaluation."""
        if record.unavailable_reason:
            msg = f"Cannot add visualization: {record.unavailable_reason}."
            raise ArtifactError(msg)
        if not self._make_room(len(data) + FILE_ENTRY_BYTES, exclude=record.identifier):
            msg = "Visualization was generated but could not be saved: MAX_STORAGE_BYTES is exhausted."
            raise ArtifactError(msg)
        path = record.directory / name
        try:
            path.write_bytes(data)
        except OSError:
            path.unlink(missing_ok=True)
            raise
        record.files[name] = len(data)
