"""Synchronous benchmark operations and resource views shared by MCP handlers."""

import io
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, NoReturn
from urllib.parse import parse_qs, quote, unquote, urlsplit
from uuid import uuid4

from PIL import Image

import ale_bench
from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.error import AleBenchError
from ale_bench.result import Result
from ale_bench.session import Session
from ale_bench_mcp.config import ServerConfig
from ale_bench_mcp.schemas import SessionStatus
from ale_bench_mcp.store import Artifact, ArtifactError, ArtifactStore


def encode_json(value: object) -> bytes:
    """Serialize public metadata without embedding image or large text blobs."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def fail(message: str) -> NoReturn:
    """Raise an anticipated error with actionable client-facing text."""
    raise ArtifactError(message)


@dataclass
class Service:
    """Own live sessions and process-local artifacts; all calls run serially."""

    config: ServerConfig
    store: ArtifactStore
    sessions: dict[str, Session] = field(default_factory=dict)

    def session(self, session_id: str) -> Session:
        """Resolve a live session without confusing restarted instances of the same problem."""
        if session_id not in self.sessions:
            fail("Session not found or closed. Call start_session(id=<problem ID>) and use its returned session id.")
        return self.sessions[session_id]

    def start(self, problem_id: str) -> dict[str, Any]:
        """Start a session using immutable operator configuration."""
        if any(session.problem_id == problem_id for session in self.sessions.values()):
            fail("A session for this problem already exists; read ale://sessions or close it before restarting.")
        if len(self.sessions) >= self.config.max_sessions:
            fail("MAX_SESSIONS reached. Close an existing session before starting another.")
        c = self.config
        session = ale_bench.start(
            problem_id=problem_id,
            lite_version=c.lite_version,
            num_workers=c.num_workers,
            run_visualization_server=c.run_visualization_server,
            use_same_time_scale=c.use_same_time_scale,
            maximum_num_case_gen=c.maximum_num_case_gen,
            maximum_num_case_eval=c.maximum_num_case_eval,
            maximum_execution_time_case_eval=c.maximum_execution_time_case_eval,
            maximum_num_call_public_eval=c.maximum_num_call_public_eval,
            session_duration=c.session_duration_seconds,
        )
        session_id = uuid4().hex
        self.sessions[session_id] = session
        return {
            "id": session_id,
            "uri": f"ale://sessions/{session_id}/status",
            "problem_uri": f"ale://problems/{quote(problem_id, safe='')}/metadata",
            "statement_uri": f"ale://problems/{quote(problem_id, safe='')}/statement",
            "tools_uri": f"ale://problems/{quote(problem_id, safe='')}/tools",
        }

    def close(self, session_id: str) -> dict[str, Any]:
        """Close runtime resources while keeping artifacts until their retention/capacity limit."""
        self.session(session_id).close()
        del self.sessions[session_id]
        return {
            "id": session_id,
            "closed": True,
            "message": "Saved artifacts remain until expiry or eviction.",
        }

    def status(self, session_id: str) -> dict[str, Any]:
        """Report budgets without private data or action_log."""
        session = self.session(session_id)
        reason = None
        try:
            finished = session.session_finished
        except AleBenchError as exc:
            finished, reason = True, str(exc)
        status = SessionStatus(
            problem_uri=f"ale://problems/{quote(session.problem_id, safe='')}/metadata",
            session_started_at=session.session_started_at,
            session_duration_seconds=session.session_duration.total_seconds(),
            remaining_time_seconds=session.session_remaining_time.total_seconds(),
            session_finished=finished,
            finished_reason=reason,
            use_same_time_scale=session.use_same_time_scale,
            maximum_resource_usage=session.maximum_resource_usage,
            current_resource_usage=session.current_resource_usage,
            remaining_resource_usage=session.remaining_resource_usage,
            next_public_eval_time=session.next_public_eval_time,
            reuse_containers=self.config.reuse_containers,
        )
        return {
            "id": session_id,
            **status.model_dump(mode="json"),
            "visualization_server_port": session.visualization_server_port,
        }

    def generate(self, session_id: str, seed: list[int] | int, gen_kwargs: dict[str, Any] | None) -> dict[str, Any]:
        """Generate once and retain inputs under a case-set ID, without returning input bodies."""
        session = self.session(session_id)
        record = self.store.begin(session_id, "case_sets")
        try:
            inputs = session.case_gen(seed=seed, gen_kwargs=gen_kwargs or {})
        except Exception:
            self.store.discard(record)
            raise
        inputs = [inputs] if isinstance(inputs, str) else inputs
        summary = {"uri": self.uri(record), "case_count": len(inputs)}
        return self.store.finish(record, summary, ((f"{i}-input", text.encode()) for i, text in enumerate(inputs)))

    @staticmethod
    def uri(record: Artifact) -> str:
        """Return the canonical URI of an operation summary."""
        return f"ale://sessions/{record.session_id}/{record.kind}/{record.identifier}"

    def evaluate(
        self,
        session_id: str,
        target: Literal["cases", "generated", "public", "private"],
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None,
        input_str: list[str] | str | None,
        job_id: str | None,
        seed: list[int] | int | None,
        gen_kwargs: dict[str, Any] | None,
        time_limit: float | None,
        memory_limit: int | str | None,
    ) -> dict[str, Any]:
        """Evaluate through the core Session API and retain only its public result."""
        session = self.session(session_id)
        local = target in {"cases", "generated"}
        if not local and any(
            value is not None for value in (input_str, job_id, seed, gen_kwargs, time_limit, memory_limit)
        ):
            fail("public/private evaluation accepts no custom cases, generation options, or time/memory limits.")
        if target == "cases":
            if (input_str is None) == (job_id is None) or seed is not None or gen_kwargs is not None:
                fail(
                    "For target=cases, provide exactly one of input_str or job_id from generate_cases; "
                    "omit seed and gen_kwargs."
                )
            if job_id is not None:
                cases = self.store.get(session_id, job_id, "case_sets")
                input_str = [self.store.read(cases, f"{i}-input").decode() for i in range(cases.summary["case_count"])]
        if target == "generated" and (input_str is not None or job_id is not None):
            fail("For target=generated, use seed/gen_kwargs; omit input_str and job_id.")
        args = {
            "code": code,
            "code_language": code_language,
            "judge_version": judge_version,
            "reuse_containers": self.config.reuse_containers,
        }
        record = self.store.begin(session_id, "evaluations")
        rank = performance = None
        try:
            if target == "private":
                result, rank, performance = session.private_eval(**args)
            elif target == "public":
                result = session.public_eval(**args, skip_local_visualization=True)
            elif target == "generated":
                result = session.case_gen_eval(
                    **args,
                    seed=0 if seed is None else seed,
                    gen_kwargs=gen_kwargs or {},
                    time_limit=time_limit,
                    memory_limit=memory_limit,
                    skip_local_visualization=True,
                )
            else:
                if input_str is None:
                    fail("No input cases were provided.")
                result = session.case_eval(
                    **args,
                    input_str=input_str,
                    time_limit=time_limit,
                    memory_limit=memory_limit,
                    skip_local_visualization=True,
                )
        except Exception:
            self.store.discard(record)
            raise
        summary = {
            "uri": self.uri(record),
            "target": target,
            "case_count": len(result.case_results),
            "overall_judge_result": result.overall_judge_result.value,
            "overall_absolute_score": result.overall_absolute_score,
            "overall_relative_score": result.overall_relative_score,
            "resource_usage": result.resource_usage.model_dump(),
            "rank": rank,
            "performance": performance,
        }
        return self.store.finish(record, summary, self._evaluation_files(result, private=target == "private"))

    @staticmethod
    def _evaluation_files(result: Result, *, private: bool) -> Iterable[tuple[str, bytes]]:
        for i, case in enumerate(result.case_results):
            metadata = case.model_dump(
                mode="json", exclude={"input_str", "output_str", "error_str", "message", "local_visualization"}
            )
            metadata["index"] = i
            metadata["fields"] = []
            if not private:
                for name, value in (
                    ("input", case.input_str),
                    ("output", case.output_str),
                    ("stderr", case.error_str),
                    ("message", case.message),
                ):
                    if value is not None:
                        yield f"{i}-{name}", value.encode()
                        metadata["fields"].append(name)
            yield f"{i}.json", encode_json(metadata)

    def run_code(
        self,
        session_id: str,
        input_str: str,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None,
        time_limit: float | None,
        memory_limit: int | str | None,
    ) -> dict[str, Any]:
        """Run raw code and keep stdout/stderr out of the tool response."""
        session = self.session(session_id)
        record = self.store.begin(session_id, "runs")
        try:
            result = session.code_run(
                input_str=input_str,
                code=code,
                code_language=code_language,
                judge_version=judge_version,
                time_limit=time_limit,
                memory_limit=memory_limit,
            )
        except Exception:
            self.store.discard(record)
            raise
        summary = {"uri": self.uri(record), **result.model_dump(exclude={"stdin", "stdout", "stderr"})}
        return self.store.finish(
            record, summary, ((name, getattr(result, name).encode()) for name in ("stdin", "stdout", "stderr"))
        )

    def visualize(self, session_id: str, job_id: str, case_index: int) -> dict[str, Any]:
        """Render one retained case without running the submitted code again."""
        record = self.store.get(session_id, job_id, "evaluations")
        if record.summary["target"] == "private":
            fail("Private evaluation inputs/outputs and visualizations are not exposed.")
        self._case_index(record, case_index)
        name = f"{case_index}-visualization"
        uri = f"{self.uri(record)}/cases/{case_index}/visualization"
        if name not in record.files:
            session = self.session(session_id)
            inputs = self.store.read(record, f"{case_index}-input").decode()
            outputs = self.store.read(record, f"{case_index}-output").decode()
            image = session.local_visualization(input_str=inputs, output_str=outputs)
            if image is None or isinstance(image, list):
                fail("Local visualization failed; no image was saved. The code was not evaluated again.")
            data = self._image(image)
            self.store.add_image(record, name, data)
        return {
            "uri": uri,
            "id": session_id,
            "job_id": job_id,
            "case_index": case_index,
            "message": "One cached image; reading this URI never reruns evaluation or visualization.",
        }

    def _image(self, image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="webp")
        data = buffer.getvalue()
        if len(data) > self.config.max_read_bytes:
            fail(f"Image exceeds MAX_READ_BYTES={self.config.max_read_bytes}; ask the operator to increase it.")
        return data

    @staticmethod
    def _case_index(record: Artifact, index: int) -> None:
        if not 0 <= index < record.summary["case_count"]:
            fail(f"Case index {index} is out of range; use 0 through {record.summary['case_count'] - 1}.")

    def read(self, uri: str) -> dict[str, Any] | bytes:
        """Read bounded views through one implementation for resources and the fallback tool."""
        self.store.prune()
        try:
            parsed = urlsplit(uri)
        except ValueError:
            fail("Malformed resource URI. Use an ale:// URI returned by this server.")
        if parsed.scheme != "ale" or parsed.fragment or parsed.netloc not in {"app", "problems", "sessions"}:
            fail("Unsupported URI. Use an ale://app, ale://problems, or ale://sessions URI returned by this server.")
        path = [unquote(part) for part in parsed.path.strip("/").split("/")] if parsed.path.strip("/") else []
        if any(part in {".", ".."} or any(c in part for c in ("/", "\\", "\x00")) for part in path):
            fail("Invalid resource path: traversal, encoded separators, and NUL bytes are not allowed.")
        query = parse_qs(parsed.query, keep_blank_values=True)
        image_path = (parsed.netloc == "problems" and len(path) == 3 and path[1] == "images") or (  # noqa: PLR2004
            parsed.netloc == "sessions" and path and path[-1] == "visualization"
        )
        if query and image_path:
            fail("Image resource URIs do not accept query parameters; remove the query to read one complete image.")
        if any(key not in {"offset", "limit"} or len(value) != 1 for key, value in query.items()):
            fail("Only one offset and one limit query parameter are supported.")
        try:
            offset = int(query.get("offset", ["0"])[0])
            limit = int(query["limit"][0]) if "limit" in query else None
        except ValueError:
            fail("offset and limit must be integers.")
        if offset < 0 or (limit is not None and limit <= 0):
            fail("offset must be nonnegative and limit must be positive.")
        if parsed.netloc == "app" and not path:
            value: dict[str, Any] | bytes = {
                "name": "ALE-Bench",
                "api": "resource-oriented",
                "synchronous": True,
                "resources": ["ale://problems", "ale://sessions"],
                "limits": {
                    key: getattr(self.config, key)
                    for key in (
                        "max_storage_bytes",
                        "max_artifacts",
                        "retention_seconds",
                        "max_read_bytes",
                        "default_read_bytes",
                        "max_page_items",
                    )
                },
            }
        elif parsed.netloc == "problems":
            value = self._read_problem(path, offset, limit)
        elif parsed.netloc == "sessions":
            value = self._read_session(path, offset, limit)
        else:
            fail("Resource not found. Read ale://app for entry points.")
        size = len(value) if isinstance(value, bytes) else len(encode_json(value))
        if size > self.config.max_read_bytes:
            fail(f"Response exceeds MAX_READ_BYTES={self.config.max_read_bytes}. Request a smaller limit.")
        return value

    def _page(self, items: Sequence[Any], offset: int, limit: int | None) -> dict[str, Any]:
        size = self.config.max_page_items if limit is None else limit
        if size > self.config.max_page_items:
            fail(f"Page limit exceeds MAX_PAGE_ITEMS={self.config.max_page_items}; request fewer items.")
        if offset > len(items):
            fail(f"offset exceeds the collection size ({len(items)}).")
        end = min(len(items), offset + size)
        return {"items": list(items[offset:end]), "total": len(items), "next_offset": end if end < len(items) else None}

    def _text(self, data: bytes, offset: int, limit: int | None, total: int | None = None) -> dict[str, Any]:
        size = self.config.default_read_bytes if limit is None else limit
        if size > self.config.max_read_bytes:
            fail(f"Text limit exceeds MAX_READ_BYTES={self.config.max_read_bytes}; request a smaller byte range.")
        total = len(data) if total is None else total
        if offset > total:
            fail(f"offset exceeds the text size ({total} bytes).")
        chunk = data[:size]
        # Preserve UTF-8 boundaries and return the next valid byte offset.
        while chunk:
            try:
                text = chunk.decode()
                break
            except UnicodeDecodeError as exc:
                if exc.start == 0 and exc.reason != "unexpected end of data":
                    fail("offset is inside a UTF-8 character; use the previous response's next_offset.")
                chunk = chunk[: exc.start]
        else:
            text = ""
        if not chunk and offset < total:
            fail("limit is too small for the next UTF-8 character; use at least 4 bytes.")
        end = offset + len(chunk)
        return {"text": text, "offset": offset, "total_bytes": total, "next_offset": end if end < total else None}

    def _text_value(self, text: str, offset: int, limit: int | None) -> dict[str, Any]:
        data = text.encode()
        return self._text(data[offset:], offset, limit, len(data))

    def _blob_text(self, record: Artifact, name: str, offset: int, limit: int | None) -> dict[str, Any]:
        size = self.config.default_read_bytes if limit is None else limit
        if size > self.config.max_read_bytes:
            fail(f"Text limit exceeds MAX_READ_BYTES={self.config.max_read_bytes}.")
        data = self.store.read(record, name, offset, size)
        return self._text(data, offset, limit, record.files[name])

    def _problem(self, problem_id: str) -> Session:
        for session in self.sessions.values():
            if session.problem_id == problem_id:
                return session
        fail(
            "Problem resource unavailable. Start a session for this problem first; problem files are released on close."
        )

    @staticmethod
    def _sources(session: Session) -> dict[str, Path]:
        root = session.rust_src_dir.resolve()
        sources = {
            f"src/{path.relative_to(root).as_posix()}": path
            for path in root.rglob("*.rs")
            if path.is_file() and path.resolve().is_relative_to(root) and not path.is_symlink()
        }
        manifest = root.parent / "Cargo.toml"
        if manifest.is_file() and not manifest.is_symlink():
            sources["Cargo.toml"] = manifest
        return sources

    def _read_problem(self, path: list[str], offset: int, limit: int | None) -> dict[str, Any] | bytes:
        if not path:
            return self._page(ale_bench.list_problem_ids(lite_version=self.config.lite_version), offset, limit)
        if len(path) < 2:  # noqa: PLR2004 -- URI segment counts.
            fail("Specify a problem resource such as /metadata, /statement, /tools, or /images.")
        session = self._problem(path[0])
        problem = session.problem
        name = "/".join(path[1:])
        base = f"ale://problems/{quote(path[0], safe='')}"
        if name == "metadata":
            return {
                "id": problem.metadata.problem_id,
                "metadata": problem.metadata.model_dump(mode="json", exclude={"problem_id"}),
                "constraints": problem.constraints.model_dump(),
                "statement_uri": f"{base}/statement",
                "images_uri": f"{base}/images",
                "tools_uri": f"{base}/tools",
            }
        texts = {
            "statement": problem.statement,
            "statement_ja": problem.statement_ja,
            "example/input": problem.example_input,
            "example/output": problem.example_output,
            "tools/README": problem.tool_readme,
        }
        if name in texts:
            text = texts[name]
            if name in {"statement", "statement_ja"}:
                image_index = 0
                for key, image_value in problem.statement_images.items():
                    image_uri = f"{base}/images/{image_index}"
                    text = text.replace(f"]({key})", f"]({image_uri})")
                    text = text.replace(f'src="{key}"', f'src="{image_uri}"')
                    image_index += len(image_value) if isinstance(image_value, list) else 1
            return self._text_value(text, offset, limit)
        if name == "public_seeds":
            return self._page(session.public_seeds, offset, limit)
        images = [
            (key, i, image)
            for key, value in problem.statement_images.items()
            for i, image in enumerate(value if isinstance(value, list) else [value])
        ]
        if name == "images":
            return self._page(
                [
                    {"name": key, "frame": frame, "uri": f"{base}/images/{i}"}
                    for i, (key, frame, _) in enumerate(images)
                ],
                offset,
                limit,
            )
        if len(path) == 3 and path[1] == "images":  # noqa: PLR2004 -- URI segment counts.
            if not path[2].isdigit() or int(path[2]) >= len(images):
                fail("Unknown problem image; read the /images index first.")
            if offset or limit is not None:
                fail("Images are read as one bounded resource; offset/limit are not supported.")
            return self._image(images[int(path[2])][2])
        sources = self._sources(session)
        if name == "tools":
            return self._page(
                [{"path": "README", "uri": f"{base}/tools/README"}]
                + [{"path": key, "uri": f"{base}/tools/{key}"} for key in sorted(sources)],
                offset,
                limit,
            )
        if name.startswith("tools/") and name.removeprefix("tools/") in sources:
            source = sources[name.removeprefix("tools/")]
            size = self.config.default_read_bytes if limit is None else limit
            if size > self.config.max_read_bytes:
                fail("Requested source range exceeds MAX_READ_BYTES.")
            with source.open("rb") as stream:
                stream.seek(offset)
                return self._text(stream.read(size), offset, limit, source.stat().st_size)
        fail("Problem resource not found or not public. Read /tools or /images for permitted file URIs.")

    def _read_session(self, path: list[str], offset: int, limit: int | None) -> dict[str, Any] | bytes:
        if not path:
            return self._page(
                [
                    {
                        "id": sid,
                        "problem_uri": f"ale://problems/{quote(session.problem_id, safe='')}/metadata",
                        "uri": f"ale://sessions/{sid}/status",
                    }
                    for sid, session in self.sessions.items()
                ],
                offset,
                limit,
            )
        if len(path) < 2:  # noqa: PLR2004 -- URI segment counts.
            fail("Specify /status, /evaluations, /case_sets, or /runs after the session ID.")
        sid, kind = path[:2]
        if kind == "status" and len(path) == 2:  # noqa: PLR2004 -- URI segment counts.
            return self.status(sid)
        if kind not in {"evaluations", "case_sets", "runs"}:
            fail("Unknown session resource; action_log and private session data are not exposed.")
        if len(path) == 2:  # noqa: PLR2004 -- URI segment counts.
            return self._page(
                [self.store.describe(r) for r in self.store.records.values() if r.session_id == sid and r.kind == kind],
                offset,
                limit,
            )
        record = self.store.get(sid, path[2], kind)
        if len(path) == 3:  # noqa: PLR2004 -- URI segment counts.
            return self.store.describe(record)
        tail = path[3:]
        if kind == "runs" and len(tail) == 1 and tail[0] in {"stdin", "stdout", "stderr"}:
            return self._blob_text(record, tail[0], offset, limit)
        if kind in {"evaluations", "case_sets"} and tail[0] == "cases":
            if len(tail) == 1:
                indices = self._page(range(record.summary["case_count"]), offset, limit)
                indices["items"] = [{"index": i, "uri": f"{self.uri(record)}/cases/{i}"} for i in indices["items"]]
                return indices
            if not tail[1].isdigit():
                fail("Case index must be a nonnegative integer.")
            index = int(tail[1])
            self._case_index(record, index)
            if len(tail) == 2:  # noqa: PLR2004 -- URI segment counts.
                if kind == "case_sets":
                    return {"index": index, "input_uri": f"{self.uri(record)}/cases/{index}/input"}
                return json.loads(self.store.read(record, f"{index}.json"))
            if len(tail) == 3:  # noqa: PLR2004 -- URI segment counts.
                if kind == "evaluations" and record.summary["target"] == "private":
                    fail("Private evaluation inputs, outputs, messages, stderr, and images are not exposed.")
                if tail[2] == "visualization" and kind == "evaluations":
                    if offset or limit is not None:
                        fail("Images do not support offset/limit; retrieve one complete image.")
                    return self.store.read(record, f"{index}-visualization")
                if tail[2] in {"input", "output", "stderr", "message"}:
                    return self._blob_text(record, f"{index}-{tail[2]}", offset, limit)
        fail("Unknown artifact resource. Read its summary or /cases index for valid paths.")
