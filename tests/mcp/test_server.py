import asyncio
import base64
import errno
import io
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, TextIO, cast
from unittest.mock import Mock

import pytest
from PIL import Image
from docker.errors import DockerException, ImageNotFound
from requests.exceptions import ConnectionError as RequestsConnectionError

pytest.importorskip("mcp.server.mcpserver", reason="Install ale-bench[mcp] to run the MCP tests")

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import MCPError
from mcp.types import BlobResourceContents, CallToolResult, TextContent, TextResourceContents

from ale_bench.data import Problem
from ale_bench.result import CaseResult, CodeRunResult, JudgeResult, ResourceUsage, Result
from ale_bench.session import Session
from ale_bench_mcp import server, service, store as store_module
from ale_bench_mcp.config import ServerConfig


@pytest.fixture(params=["auto", "legacy"])
def mode(request: pytest.FixtureRequest) -> Literal["auto", "legacy"]:
    return request.param


@pytest.fixture(autouse=True)
def config_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for field in ServerConfig.model_fields:
        monkeypatch.delenv(f"ALE_BENCH_MCP_{field.upper()}", raising=False)
    monkeypatch.setenv("ALE_BENCH_MCP_STORAGE_DIRECTORY", str(tmp_path))


def make_session(root: Path) -> Session:
    # Real core status/budget checks, but no Docker, downloads, or compiler.
    session = object.__new__(Session)
    session._problem = Problem.model_validate(
        {
            "metadata": {
                "problem_id": "ahc001",
                "start_at": "2025-01-01T00:00:00Z",
                "end_at": "2025-01-02T00:00:00Z",
                "contest_url": "https://atcoder.jp/contests/ahc001",
                "title": "Test problem",
                "problem_type": "batch",
                "score_type": "maximize",
            },
            "constraints": {"time_limit": 2.0, "memory_limit": 1024},
            "statement": "Statement: ![example](example.png)",
            "statement_ja": "日本語の問題文",
            "statement_images": {"example.png": Image.new("RGB", (3, 4), "blue")},
            "example_input": "input",
            "example_output": "output",
            "tool_readme": "Rust tool README",
        }
    )
    session._tool_dir = root
    source = root / "tools" / "src"
    (source / "bin").mkdir(parents=True, exist_ok=True)
    (source / "lib.rs").write_text("// library\n", encoding="utf-8")
    (source / "bin" / "gen.rs").write_text("// generator\n", encoding="utf-8")
    (source / "bin" / "vis.rs").write_text("// visualizer\n", encoding="utf-8")
    (source.parent / "Cargo.toml").write_text('[package]\nname="tools"\n', encoding="utf-8")
    (root / "private.txt").write_text("PRIVATE SECRET", encoding="utf-8")
    session._session_started_at = datetime.now(tz=UTC)
    session._session_duration = timedelta(hours=1)
    session._use_same_time_scale = True
    session._last_public_eval_time = session._session_started_at
    session._maximum_resource_usage = ResourceUsage(
        num_case_gen=10, num_case_eval=20, num_call_public_eval=3, num_call_private_eval=1, execution_time_case_eval=100
    )
    session._current_resource_usage = ResourceUsage(num_case_gen=10, num_case_eval=2, execution_time_case_eval=5)
    session._visualization_server_port = 8080
    session._public_seeds = [1, 2]
    session._action_log = ["SECRET ACTION LOG"]
    session.close = Mock()
    result = Result(
        allow_score_non_ac=True,
        resource_usage=ResourceUsage(num_case_eval=2, execution_time_case_eval=0.5),
        case_results=[
            CaseResult(
                input_str=f"input-{i}",
                output_str=f"出力-{i}",
                error_str="stderr",
                message="accepted",
                judge_result=JudgeResult.ACCEPTED,
                absolute_score=100 + i,
                execution_time=0.25,
                memory_usage=1024,
            )
            for i in range(2)
        ],
    )
    session.case_gen = Mock(return_value=["generated 0", "generated 1"])
    session.case_eval = Mock(return_value=result)
    session.case_gen_eval = Mock(return_value=result)
    session.public_eval = Mock(return_value=result)
    # Deliberately return unredacted mock fields: the adapter must still never persist them for private evaluation.
    session.private_eval = Mock(return_value=(result, 7, 1500))
    session.code_run = Mock(
        return_value=CodeRunResult(
            stdin="input", stdout="output", stderr="stderr", exit_status=0, execution_time=0.1, memory_usage=1024
        )
    )
    session.local_visualization = Mock(return_value=Image.new("RGB", (3, 4), "blue"))
    return session


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Session:
    value = make_session(tmp_path / "problem")
    monkeypatch.setattr(service.ale_bench, "start", Mock(return_value=value))
    monkeypatch.setattr(service.ale_bench, "list_problem_ids", Mock(return_value=["ahc001", "ahc002"]))
    return value


async def call(client: Client, name: str, **arguments: object) -> dict[str, Any]:
    response = await client.call_tool(name, arguments)
    assert not response.is_error, response
    assert response.structured_content is not None
    return response.structured_content


async def read(client: Client, uri: str) -> dict[str, Any]:
    result = await client.read_resource(uri)
    assert isinstance(result.contents[0], TextResourceContents)
    return json.loads(result.contents[0].text)


def error_text(result: CallToolResult) -> str:
    assert isinstance(result.content[0], TextContent)
    return result.content[0].text


async def both_error(client: Client, uri: str, message: str) -> None:
    with pytest.raises(MCPError, match=message):
        await client.read_resource(uri)
    result = await client.call_tool("read_resource", {"uri": uri})
    assert result.is_error
    assert message in error_text(result)


def test_discovery_and_problem_resources(mode: Literal["auto", "legacy"], session: Session) -> None:
    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            tools = (await client.list_tools()).tools
            assert {t.name for t in tools} == {
                "start_session",
                "close_session",
                "generate_cases",
                "evaluate",
                "code_run",
                "visualize_case",
                "read_resource",
            }
            for tool in tools:
                properties = tool.input_schema["properties"]
                # These names are consumed as client metadata by Claude Desktop's MCP bridge.
                assert not {"session_id", "trigger_id", "ccr_card_approval", "image_max_px"} & properties.keys()
                assert (
                    not {"problem_id", "ale_session_id", "artifact_id", "case_set_id", "evaluation_id"}
                    & properties.keys()
                )
                assert "ctx" not in properties
                assert "reuse_containers" not in properties
                if tool.name == "start_session":
                    assert set(properties) == {"id"}
                    assert tool.input_schema["required"] == ["id"]
                    assert "Problem ID" in properties["id"]["description"]
                elif tool.name != "read_resource":
                    assert "id" in tool.input_schema["required"]
                    assert "start_session" in properties["id"]["description"]
                if tool.name == "evaluate":
                    assert "generate_cases" in properties["job_id"]["description"]
                if tool.name == "visualize_case":
                    assert "job_id" in tool.input_schema["required"]
                    assert "evaluate" in properties["job_id"]["description"]
            templates = (await client.list_resource_templates()).resource_templates
            assert any("ale://problems/{id}" in t.uri_template for t in templates)
            assert any("ale://sessions/{id}/evaluations/{job_id}" in t.uri_template for t in templates)
            assert (await read(client, "ale://app"))["synchronous"] is True
            assert (await read(client, "ale://problems?limit=1"))["items"] == ["ahc001"]
            started = await call(client, "start_session", id="ahc001")
            sid = started["id"]
            assert sid != "ahc001"
            assert not {"problem_id", "session_id", "ale_session_id"} & started.keys()
            status = await read(client, started["uri"])
            assert status["id"] == sid
            assert status["problem_uri"] == started["problem_uri"]
            assert "problem_id" not in status
            assert status["remaining_resource_usage"]["num_case_gen"] == 0
            assert (await read(client, "ale://sessions"))["items"] == [
                {"id": sid, "problem_uri": started["problem_uri"], "uri": started["uri"]}
            ]
            metadata = await read(client, started["problem_uri"])
            assert metadata["id"] == "ahc001"
            assert "problem_id" not in metadata["metadata"]
            assert metadata["constraints"]["time_limit"] == 2.0
            assert "statement_images" not in metadata
            assert "Statement" in (await read(client, started["statement_uri"]))["text"]
            native = await read(client, "ale://problems/ahc001/statement_ja?limit=6")
            assert native["text"] == "日本"
            assert native["next_offset"] == 6
            assert await call(client, "read_resource", uri="ale://problems/ahc001/statement_ja?limit=6") == native
            tools_page = await read(client, started["tools_uri"])
            assert {item["path"] for item in tools_page["items"]} == {
                "README",
                "Cargo.toml",
                "src/lib.rs",
                "src/bin/gen.rs",
                "src/bin/vis.rs",
            }
            assert (await read(client, "ale://problems/ahc001/tools/src/bin/gen.rs"))["text"] == "// generator\n"
            assert (await read(client, "ale://problems/ahc001/public_seeds"))["items"] == [1, 2]
            images = await read(client, "ale://problems/ahc001/images")
            image = (await client.read_resource(images["items"][0]["uri"])).contents[0]
            assert isinstance(image, BlobResourceContents)
            assert image.mime_type == "image/webp"
            assert Image.open(io.BytesIO(base64.b64decode(image.blob))).size == (3, 4)
            await both_error(client, f"ale://sessions/{sid}/action_log", "not exposed")
            await both_error(client, "ale://problems/ahc001/tools/private.txt", "not public")
            assert (await call(client, "close_session", id=sid))["id"] == sid
            await both_error(client, started["statement_uri"], "Start a session")
            restarted = await call(client, "start_session", id="ahc001")
            assert restarted["id"] != sid
            await both_error(client, started["uri"], "Session not found")

    asyncio.run(run())


@pytest.mark.parametrize("target", ["cases", "generated", "public", "private"])
@pytest.mark.parametrize("reuse", [True, False])
def test_evaluation_artifacts(
    mode: Literal["auto", "legacy"], session: Session, target: str, reuse: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALE_BENCH_MCP_REUSE_CONTAINERS", str(reuse))

    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            args = {"input_str": ["a", "b"]} if target == "cases" else {}
            result = await call(client, "evaluate", id=sid, target=target, code="code", code_language="python", **args)
            assert result["id"] == sid
            assert result["kind"] == "evaluations"
            assert not {"artifact_id", "evaluation_id", "ale_session_id"} & result.keys()
            assert result["overall_absolute_score"] == 201
            assert result["case_count"] == 2
            assert result["details_available"] is True
            assert "case_results" not in result
            method = {
                "cases": session.case_eval,
                "generated": session.case_gen_eval,
                "public": session.public_eval,
                "private": session.private_eval,
            }[target]
            assert isinstance(method, Mock)
            assert method.call_args.kwargs["reuse_containers"] is reuse
            if target != "private":
                assert method.call_args.kwargs["skip_local_visualization"] is True
            uri = result["uri"]
            assert (await read(client, uri))["job_id"] == result["job_id"]
            assert len((await read(client, uri + "/cases?limit=1"))["items"]) == 1
            assert (await read(client, uri + "/cases/0"))["absolute_score"] == 100
            if target == "private":
                assert (result["rank"], result["performance"]) == (7, 1500)
                for field in ["input", "output", "stderr", "message", "visualization"]:
                    await both_error(client, uri + "/cases/0/" + field, "Private evaluation")
                response = await client.call_tool(
                    "visualize_case", {"id": sid, "job_id": result["job_id"], "case_index": 0}
                )
                assert response.is_error
                cast("Mock", session.local_visualization).assert_not_called()
            else:
                assert (await read(client, uri + "/cases/0/output"))["text"] == "出力-0"
                await both_error(client, uri + "/cases/0/visualization", "not available")
                image = await call(client, "visualize_case", id=sid, job_id=result["job_id"], case_index=0)
                assert image["id"] == sid
                assert image["job_id"] == result["job_id"]
                await call(client, "visualize_case", id=sid, job_id=result["job_id"], case_index=0)
                cast("Mock", session.local_visualization).assert_called_once_with(
                    input_str="input-0", output_str="出力-0"
                )
                assert (await client.read_resource(image["uri"])).contents[0].mime_type == "image/webp"
                fallback = await client.call_tool("read_resource", {"uri": image["uri"]})
                assert fallback.content[0].type == "image"
            method.assert_called_once()
            await call(client, "close_session", id=sid)
            assert (await read(client, uri))["overall_absolute_score"] == 201
            await both_error(client, uri.replace(sid, "other-session"), "does not belong")

    asyncio.run(run())


def test_generated_cases_and_code_run(mode: Literal["auto", "legacy"], session: Session) -> None:
    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            cases = await call(client, "generate_cases", id=sid, seed=[0, 1])
            assert cases["id"] == sid
            assert cases["kind"] == "case_sets"
            assert cases["case_count"] == 2
            assert (await read(client, cases["uri"] + "/cases/1/input"))["text"] == "generated 1"
            evaluated = await call(
                client,
                "evaluate",
                id=sid,
                target="cases",
                job_id=cases["job_id"],
                code="code",
                code_language="python",
            )
            assert evaluated["job_id"] != cases["job_id"]
            assert evaluated["kind"] == "evaluations"
            cast("Mock", session.case_eval).assert_called_once()
            assert cast("Mock", session.case_eval).call_args.kwargs["input_str"] == ["generated 0", "generated 1"]
            cast("Mock", session.case_gen).assert_called_once()
            result = await call(client, "code_run", id=sid, input_str="input", code="code", code_language="python")
            assert result["id"] == sid
            assert result["kind"] == "runs"
            assert result["job_id"] not in {cases["job_id"], evaluated["job_id"]}
            assert result["exit_status"] == 0
            assert "stdout" not in result
            assert (await read(client, result["uri"]))["id"] == sid
            assert (await read(client, f"ale://sessions/{sid}/runs"))["items"][0]["id"] == sid
            assert (await read(client, result["uri"] + "/stdout"))["text"] == "output"

    asyncio.run(run())


def test_job_reference_errors(mode: Literal["auto", "legacy"], session: Session) -> None:
    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            cases = await call(client, "generate_cases", id=sid)
            evaluated = await call(client, "evaluate", id=sid, target="generated", code="code", code_language="python")
            executed = await call(client, "code_run", id=sid, input_str="input", code="code", code_language="python")
            for wrong_job in (evaluated, executed):
                result = await client.call_tool(
                    "evaluate",
                    {
                        "id": sid,
                        "target": "cases",
                        "job_id": wrong_job["job_id"],
                        "code": "code",
                        "code_language": "python",
                    },
                )
                assert result.is_error
                assert f"kind={wrong_job['kind']}; expected case_sets" in error_text(result)
                assert f"ale://sessions/{sid}/case_sets" in error_text(result)
            for wrong_job in (cases, executed):
                result = await client.call_tool(
                    "visualize_case", {"id": sid, "job_id": wrong_job["job_id"], "case_index": 0}
                )
                assert result.is_error
                assert f"kind={wrong_job['kind']}; expected evaluations" in error_text(result)
            for target, extra, message in [
                ("cases", {"input_str": "input"}, "exactly one of input_str or job_id from generate_cases"),
                ("generated", {}, "omit input_str and job_id"),
                ("public", {}, "accepts no custom cases"),
            ]:
                result = await client.call_tool(
                    "evaluate",
                    {
                        "id": sid,
                        "target": target,
                        "job_id": cases["job_id"],
                        "code": "code",
                        "code_language": "python",
                        **extra,
                    },
                )
                assert result.is_error
                assert message in error_text(result)
            await call(client, "close_session", id=sid)
            restarted_id = (await call(client, "start_session", id="ahc001"))["id"]
            result = await client.call_tool(
                "evaluate",
                {
                    "id": restarted_id,
                    "target": "cases",
                    "job_id": cases["job_id"],
                    "code": "code",
                    "code_language": "python",
                },
            )
            assert result.is_error
            assert f"does not belong to session id={restarted_id}" in error_text(result)
            cast("Mock", session.case_eval).assert_not_called()
            cast("Mock", session.local_visualization).assert_not_called()
            cast("Mock", session.public_eval).assert_not_called()
            cast("Mock", session.case_gen_eval).assert_called_once()

    asyncio.run(run())


@pytest.mark.parametrize("state", ["active", "expired", "submitted"])
def test_status_and_core_errors(
    mode: Literal["auto", "legacy"], session: Session, state: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Exercise actual core budget checks before Docker would be reached.
    monkeypatch.delattr(session, "case_gen")
    monkeypatch.delattr(session, "public_eval")
    if state == "expired":
        session._session_started_at -= timedelta(hours=2)
    if state == "submitted":
        session._current_resource_usage += ResourceUsage(num_call_private_eval=1)

    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            started = await call(client, "start_session", id="ahc001")
            assert (await read(client, started["uri"]))["session_finished"] == (state != "active")
            response = await client.call_tool("generate_cases", {"id": started["id"]})
            assert response.is_error
            assert ("maximum resource usage" if state == "active" else "session is finished") in error_text(response)
            if state == "active":
                response = await client.call_tool(
                    "evaluate",
                    {
                        "id": started["id"],
                        "target": "public",
                        "code": "code",
                        "code_language": "python",
                    },
                )
                assert response.is_error
                assert "next public evaluation" in error_text(response)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("suffix", "message"),
    [
        ("?offset=-1", "nonnegative"),
        ("?limit=0", "positive"),
        ("?limit=abc", "integers"),
        ("?limit=99999999", "MAX_READ_BYTES"),
        ("?offset=9999999", "text size"),
        ("?offset=1", "UTF-8"),
        ("?limit=1", "UTF-8"),
    ],
)
def test_read_errors(mode: Literal["auto", "legacy"], session: Session, suffix: str, message: str) -> None:
    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            await call(client, "start_session", id="ahc001")
            await both_error(client, "ale://problems/ahc001/statement_ja" + suffix, message)

    asyncio.run(run())


def test_storage_capacity_and_expiry(
    mode: Literal["auto", "legacy"], session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALE_BENCH_MCP_MAX_STORAGE_BYTES", "16384")
    cast("Mock", session.case_gen).return_value = ["x" * 20000]

    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            result = await call(client, "generate_cases", id=sid)
            assert result["details_available"] is False
            assert "storage_limit" in result["unavailable_reason"]
            assert (await read(client, result["uri"]))["case_count"] == 1
            await both_error(client, result["uri"] + "/cases/0/input", "storage_limit")
            cast("Mock", session.case_gen).assert_called_once()
            # Advance only this store's clock, not the SDK/asyncio clock.

            monkeypatch.setattr(store_module, "time", Mock(monotonic=Mock(return_value=10**12)))
            await both_error(client, result["uri"], "expired")

    asyncio.run(run())


def test_operator_settings_and_limits(
    mode: Literal["auto", "legacy"], session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALE_BENCH_MCP_MAXIMUM_NUM_CASE_EVAL", "5")
    monkeypatch.setenv("ALE_BENCH_MCP_MAX_SESSIONS", "1")
    monkeypatch.setenv("ALE_BENCH_MCP_MAX_PAGE_ITEMS", "1")
    monkeypatch.setenv("ALE_BENCH_MCP_REUSE_CONTAINERS", "false")

    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            monkeypatch.setenv("ALE_BENCH_MCP_MAXIMUM_NUM_CASE_EVAL", "999")
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            assert cast("Mock", service.ale_bench.start).call_args.kwargs["maximum_num_case_eval"] == 5
            assert (await read(client, f"ale://sessions/{sid}/status"))["reuse_containers"] is False
            response = await client.call_tool("start_session", {"id": "ahc002"})
            assert response.is_error
            assert "MAX_SESSIONS" in error_text(response)
            await both_error(client, "ale://problems?limit=2", "MAX_PAGE_ITEMS")
            response = await client.call_tool(
                "evaluate",
                {
                    "id": sid,
                    "target": "public",
                    "input_str": "not allowed",
                    "code": "code",
                    "code_language": "python",
                },
            )
            assert response.is_error
            cast("Mock", session.public_eval).assert_not_called()

    asyncio.run(run())


@pytest.mark.parametrize("entrypoint", ["console", "module"])
def test_stdio_entrypoints(mode: Literal["auto", "legacy"], entrypoint: str, tmp_path: Path) -> None:
    if entrypoint == "console":
        command, args = str(Path(sys.executable).with_name("ale-bench-mcp")), []
    else:
        command, args = sys.executable, ["-m", "ale_bench_mcp"]

    async def run() -> None:
        params = StdioServerParameters(command=command, args=args, cwd=str(tmp_path), env=dict(os.environ))
        async with Client(params, mode=mode, read_timeout_seconds=10) as client:
            assert (await read(client, "ale://app"))["synchronous"] is True
            assert (await call(client, "read_resource", uri="ale://sessions"))["items"] == []

    asyncio.run(run())


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (FileNotFoundError(errno.ENOENT, "operator-only details", "/private/hidden.dat"), "FileNotFoundError (ENOENT:"),
        (PermissionError(errno.EACCES, "operator-only details", "/private/hidden.dat"), "PermissionError (EACCES:"),
        (OSError(errno.ENOSPC, "operator-only details", "/private/hidden.dat"), "OSError (ENOSPC:"),
        (RequestsConnectionError("operator-only connection details"), "ConnectionError"),
        (ImageNotFound("operator-only image details"), "ImageNotFound. Required Docker image is unavailable"),
        (DockerException("operator-only daemon details"), "DockerException. Check the Docker daemon"),
    ],
)
def test_environment_error_diagnostics(
    mode: Literal["auto", "legacy"],
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure: Exception,
    reason: str,
) -> None:
    cast("Mock", session.case_eval).side_effect = failure
    monkeypatch.setattr(service.Service, "_sources", Mock(side_effect=failure))

    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            result = await client.call_tool(
                "evaluate",
                {"id": sid, "target": "cases", "input_str": "input", "code": "code", "code_language": "python"},
            )
            assert result.is_error
            with pytest.raises(MCPError) as native:
                await client.read_resource("ale://problems/ahc001/tools")
            fallback = await client.call_tool("read_resource", {"uri": "ale://problems/ahc001/tools"})
            assert fallback.is_error
            messages = [error_text(result), str(native.value), error_text(fallback)]
            records = [record for record in caplog.records if record.name == "ale_bench_mcp.server"]
            for message, operation, record in zip(
                messages, ["evaluate", "problem_resource", "read_resource"], records, strict=True
            ):
                assert f"{operation} failed with {reason}" in message
                assert "operator-only" not in message
                assert "hidden.dat" not in message
                reference = message.split("reference=", 1)[1].split(")", 1)[0]
                assert reference in record.getMessage()
                assert f"MCP operation {operation} failed" in record.getMessage()
                assert record.exc_info is not None
                assert record.exc_info[1] is failure
                assert record.exc_info[2] is not None
            assert (await read(client, f"ale://sessions/{sid}/status"))["id"] == sid

    asyncio.run(run())


def test_stdio_jobs_and_error_visibility(mode: Literal["auto", "legacy"], tmp_path: Path) -> None:
    script = f"""
import runpy
from pathlib import Path
from ale_bench_mcp import service
from ale_bench_mcp.__main__ import main
from ale_bench.error import AleBenchError
make_session = runpy.run_path({str(Path(__file__).resolve())!r})['make_session']
session = make_session(Path({str(tmp_path / "fake")!r}))
def start(problem_id, **kwargs):
    if problem_id == 'expected':
        raise AleBenchError('Expected budget error')
    if problem_id == 'unexpected':
        raise RuntimeError('Secret implementation details')
    if problem_id == 'io':
        raise FileNotFoundError(2, 'operator-only details', '/private/hidden.dat')
    return session
service.ale_bench.start = start
main()
"""

    async def run(errlog: TextIO) -> None:
        params = StdioServerParameters(command=sys.executable, args=["-c", script], env=dict(os.environ))
        async with Client(stdio_client(params, errlog=errlog), mode=mode, read_timeout_seconds=10) as client:
            expected = await client.call_tool("start_session", {"id": "expected"})
            assert expected.is_error
            assert "Expected budget error" in error_text(expected)
            unexpected = await client.call_tool("start_session", {"id": "unexpected"})
            assert unexpected.is_error
            assert "Secret implementation details" not in error_text(unexpected)
            io_error = await client.call_tool("start_session", {"id": "io"})
            assert io_error.is_error
            assert "FileNotFoundError (ENOENT:" in error_text(io_error)
            assert "reference=" in error_text(io_error)
            assert "hidden.dat" not in error_text(io_error)
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            # Reproduce the reported request through Claude Desktop's metadata-stripping behavior.
            # Core execution is mocked; this checks MCP argument validation, routing, and resource access.
            arguments = {
                "session_id": "claude-conversation-id",
                "trigger_id": "claude-trigger-id",
                "ccr_card_approval": "claude-approval",
                "image_max_px": 1024,
                "id": sid,
                "code": '#include <bits/stdc++.h> int main(){puts("M D");}',
                "code_language": "cpp20",
                "input_str": "20 2\n0 0\n1 0\n",
            }
            forwarded = {
                key: value
                for key, value in arguments.items()
                if key not in {"session_id", "trigger_id", "ccr_card_approval", "image_max_px"}
            }
            missing_id = await client.call_tool(
                "code_run", {key: value for key, value in forwarded.items() if key != "id"}
            )
            assert missing_id.is_error
            assert "id" in error_text(missing_id)
            assert "Field required" in error_text(missing_id)
            run_result = await call(client, "code_run", **forwarded)
            assert run_result["id"] == sid
            assert run_result["exit_status"] == 0
            assert (await read(client, run_result["uri"] + "/stdout"))["text"] == "output"
            cases = await call(client, "generate_cases", id=sid, seed=[0, 1])
            evaluation = await call(
                client, "evaluate", id=sid, target="cases", job_id=cases["job_id"], code="code", code_language="python"
            )
            assert len({cases["job_id"], evaluation["job_id"], run_result["job_id"]}) == 3
            assert (await read(client, evaluation["uri"] + "/cases/0/output"))["text"] == "出力-0"
            image = await call(client, "visualize_case", id=sid, job_id=evaluation["job_id"], case_index=0)
            assert (await client.read_resource(image["uri"])).contents[0].mime_type == "image/webp"
            await both_error(client, evaluation["uri"] + "/cases/99/output", "out of range")

    log_path = tmp_path / "server-stderr.log"
    with log_path.open("w") as errlog:
        asyncio.run(run(errlog))
    stderr = log_path.read_text()
    assert "MCP operation start_session failed" in stderr
    assert "hidden.dat" in stderr


def test_read_byte_limit_and_traversal(
    mode: Literal["auto", "legacy"], session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ALE_BENCH_MCP_MAX_READ_BYTES", "4096")
    monkeypatch.setenv("ALE_BENCH_MCP_DEFAULT_READ_BYTES", "1000")
    # JSON escaping can expand the payload beyond the raw chunk size.
    cast("Mock", session.case_gen).return_value = ["\x01" * 2000]
    (session.rust_src_dir / "leak.rs").symlink_to(tmp_path / "problem" / "private.txt")

    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            generated = await call(client, "generate_cases", id=sid)
            uri = generated["uri"] + "/cases/0/input"
            await both_error(client, uri + "?limit=1000", "MAX_READ_BYTES")
            response = await client.read_resource(uri + "?limit=500")
            assert isinstance(response.contents[0], TextResourceContents)
            assert len(response.contents[0].text.encode()) <= 4096
            assert (await read(client, uri + "?offset=500&limit=500"))["next_offset"] == 1000
            await both_error(client, "ale://problems/ahc001/tools/src/leak.rs", "not public")
            for path in ["../private.txt", "%2e%2e/private.txt", "%252e%252e/private.txt"]:
                result = await client.call_tool("read_resource", {"uri": f"ale://problems/ahc001/tools/{path}"})
                assert result.is_error
                assert "PRIVATE SECRET" not in error_text(result)
                with pytest.raises(MCPError):
                    await client.read_resource(f"ale://problems/ahc001/tools/{path}")

    asyncio.run(run())


def test_operations_stay_on_event_loop(mode: Literal["auto", "legacy"], session: Session) -> None:
    async def run() -> None:
        loop = asyncio.get_running_loop()
        events = []
        result = cast("Mock", session.case_eval).return_value

        def evaluate_sync(**_kwargs: object) -> Result:
            assert asyncio.get_running_loop() is loop  # Would fail if SDK offloaded the handler to a worker.
            events.append("begin")
            loop.call_soon(events.append, "scheduled")
            events.append("end")
            return result

        cast("Mock", session.case_eval).side_effect = evaluate_sync
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            await call(
                client,
                "evaluate",
                id=sid,
                target="cases",
                input_str="input",
                code="code",
                code_language="python",
            )
            await asyncio.sleep(0)
            assert events == ["begin", "end", "scheduled"]

    asyncio.run(run())


def test_cleanup_storage_on_shutdown(mode: Literal["auto", "legacy"], session: Session, tmp_path: Path) -> None:
    async def run() -> None:
        async with Client(server.mcp, mode=mode) as client:
            sid = (await call(client, "start_session", id="ahc001"))["id"]
            await call(client, "generate_cases", id=sid)
            assert list(tmp_path.glob("ale-bench-mcp-*"))  # noqa: ASYNC240 -- Intentionally synchronous server.
        assert not list(tmp_path.glob("ale-bench-mcp-*"))  # noqa: ASYNC240 -- Intentionally synchronous server.
        cast("Mock", session.close).assert_called_once()

    asyncio.run(run())
