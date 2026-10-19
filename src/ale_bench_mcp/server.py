"""Resource-oriented MCP adapter; benchmark calls deliberately block other requests."""

# ruff: noqa: A002 -- The public MCP parameter is intentionally named id.

import errno
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any, Literal, ParamSpec, TypeVar
from urllib.parse import quote, urlencode
from uuid import uuid4

from docker.errors import DockerException, ImageNotFound
from mcp.server.mcpserver import Context, Image, MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import CallToolResult, ResourceLink, TextContent
from pydantic import Field

from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.error import AleBenchError
from ale_bench_mcp.config import ServerConfig
from ale_bench_mcp.service import Service, encode_json
from ale_bench_mcp.store import ArtifactError, ArtifactStore

P = ParamSpec("P")
T = TypeVar("T")
logger = logging.getLogger(__name__)

# Claude Desktop's bridge consumes session_id as client metadata before forwarding tool arguments.
ProblemId = Annotated[str, Field(description="Problem ID from ale://problems, such as ahc001.")]
SessionId = Annotated[
    str,
    Field(description="ALE-Bench session ID returned as id by start_session; list active IDs at ale://sessions."),
]


def client_errors(*, resource: bool = False) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Expose anticipated errors on both protocol surfaces without exposing arbitrary tracebacks."""

    def decorate(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        operation = getattr(func, "__name__", type(func).__name__)

        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except (AleBenchError, ArtifactError) as exc:
                error = ResourceError if resource else ToolError
                raise error(str(exc)) from exc
            except (DockerException, OSError) as exc:
                error = ResourceError if resource else ToolError
                reference = uuid4().hex[:12]
                logger.exception("MCP operation %s failed (reference=%s, pid=%s)", operation, reference, os.getpid())
                reason = type(exc).__name__
                advice = "Check the failing file, connection, or execution environment."
                if isinstance(exc, ImageNotFound):
                    advice = (
                        "Required Docker image is unavailable. Build the ALE-Bench language/judge image "
                        "for the server's user ID with the required local tag; the image name is in the log."
                    )
                elif isinstance(exc, DockerException):
                    advice = "Check the Docker daemon, image availability, and container configuration."
                elif exc.errno is not None:
                    reason += f" ({errno.errorcode.get(exc.errno, exc.errno)}: {os.strerror(exc.errno)})"
                msg = (
                    f"{operation} failed with {reason}. {advice} "
                    f"Ask the operator to check the server stderr log (reference={reference}). "
                    "The operation may have consumed budget; check session status before retrying."
                )
                raise error(msg) from exc

        return wrapped

    return decorate


@asynccontextmanager
async def app_lifespan(_server: MCPServer[Service]) -> AsyncGenerator[Service, None]:
    """Load immutable configuration and clean up only this process's artifact directory."""
    config = ServerConfig.from_env()
    with TemporaryDirectory(prefix="ale-bench-mcp-", dir=config.storage_directory) as directory:
        store = ArtifactStore(Path(directory), config.max_storage_bytes, config.max_artifacts, config.retention_seconds)
        service = Service(config, store)
        try:
            yield service
        finally:
            # Keep cleanup progressing even when one session cannot release its Docker resources.
            failures = []
            for session in service.sessions.values():
                try:
                    session.close()
                except Exception as exc:
                    failures.append(exc)
            if failures:
                msg = "Failed to close ALE-Bench sessions"
                raise ExceptionGroup(msg, failures)


# Do not turn these into sync def handlers (SDK v2 would offload them to threads).
# No awaits during core operations: budget mutations stay serialized on the event loop.
mcp = MCPServer("ALE-Bench MCP Server", dependencies=["ale_bench"], lifespan=app_lifespan)


def service(ctx: Context[Service]) -> Service:
    """Resolve the application service from the request context."""
    return ctx.request_context.lifespan_context


def reply(data: dict[str, Any]) -> CallToolResult:
    """Return a compact summary and an actual MCP resource link when available."""
    content: list[Any] = [TextContent(type="text", text=encode_json(data).decode())]
    if "uri" in data:
        content.append(ResourceLink(type="resource_link", uri=data["uri"], name=data.get("job_id", "resource")))
    return CallToolResult(content=content, structured_content=data)


def native(value: dict[str, Any] | bytes) -> str | bytes:
    """Avoid SDK pretty-printing beyond the checked resource byte limit."""
    return value if isinstance(value, bytes) else encode_json(value).decode()


def uri_with_query(base: str, offset: str, limit: str | None) -> str:
    """Build the same canonical read request for resources and the fallback tool."""
    query = {"offset": offset}
    if limit is not None:
        query["limit"] = limit
    return f"{base}?{urlencode(query)}"


@mcp.tool()
@client_errors()
async def start_session(ctx: Context[Service], id: ProblemId) -> CallToolResult:
    """Start the problem identified by id; return a new session id and problem/status resource links.

    Read ale://problems for IDs. Problem statement, Rust sources, and images are loaded
    through resources after starting. Budget/configuration overrides are not accepted.
    Pass the returned session id to subsequent tools; it differs from the input problem id
    and is specific to this server process.
    """
    return reply(service(ctx).start(id))


@mcp.tool()
@client_errors()
async def close_session(ctx: Context[Service], id: SessionId) -> CallToolResult:
    """Close a session; saved results remain readable until expiry/eviction."""
    return reply(service(ctx).close(id))


@mcp.tool()
@client_errors()
async def generate_cases(
    ctx: Context[Service],
    id: SessionId,
    seed: list[int] | int = 0,
    gen_kwargs: dict[str, Any] | None = None,
) -> CallToolResult:
    """Generate cases using the core budget checks and return a case-set job_id, never bulk input text.

    Pass job_id as evaluate(job_id=...) or read /cases/{index}/input.
    If details_available=false, generation completed but its inputs could not be retained.
    """
    return reply(service(ctx).generate(id, seed, gen_kwargs))


@mcp.tool()
@client_errors()
async def evaluate(
    ctx: Context[Service],
    id: SessionId,
    target: Literal["cases", "generated", "public", "private"],
    code: str,
    code_language: CodeLanguage | str,
    judge_version: JudgeVersion | str | None = None,
    input_str: list[str] | str | None = None,
    job_id: Annotated[
        str | None,
        Field(description="For target=cases only: job_id returned by generate_cases in this session; omit input_str."),
    ] = None,
    seed: list[int] | int | None = None,
    gen_kwargs: dict[str, Any] | None = None,
    time_limit: float | None = None,
    memory_limit: int | str | None = None,
) -> CallToolResult:
    """Evaluate once and return a new evaluation job_id, scores, budget consumption, and a resource link.

    cases: supply input_str OR a job_id returned by generate_cases in this session.
    The returned job_id identifies this new evaluation, not the input case-set job.
    generated: use seed (default 0) and gen_kwargs; core case_gen_eval owns both budgets.
    public/private: use fixed benchmark cases/limits; omit all local case/generation/limit options.
    Private evaluation is one-shot and exposes only redacted scores/statistics.
    Read /cases for indices and /cases/{index} for metadata; select one case for visualize_case.
    details_available=false means evaluation DID complete; do not retry just to recover its details.
    """
    return reply(
        service(ctx).evaluate(
            id,
            target,
            code,
            code_language,
            judge_version,
            input_str,
            job_id,
            seed,
            gen_kwargs,
            time_limit,
            memory_limit,
        )
    )


@mcp.tool()
@client_errors()
async def code_run(
    ctx: Context[Service],
    id: SessionId,
    input_str: str,
    code: str,
    code_language: CodeLanguage | str,
    judge_version: JudgeVersion | str | None = None,
    time_limit: float | None = None,
    memory_limit: int | str | None = None,
) -> CallToolResult:
    """Run arbitrary code through the core API; return job_id, statistics, and links to retained stdin/stdout/stderr."""
    return reply(service(ctx).run_code(id, input_str, code, code_language, judge_version, time_limit, memory_limit))


@mcp.tool()
@client_errors()
async def visualize_case(
    ctx: Context[Service],
    id: SessionId,
    job_id: Annotated[str, Field(description="job_id returned by evaluate in this session.")],
    case_index: int,
) -> CallToolResult:
    """Generate/cache one image from retained evaluation input/output, without reevaluating code.

    Requires a live, unfinished session on the first call; cached images remain readable
    after close until expiry/eviction. Private evaluations cannot be visualized.
    The returned job_id is the source evaluation job; no new job is created.
    """
    return reply(service(ctx).visualize(id, job_id, case_index))


@mcp.tool()
@client_errors()
async def read_resource(ctx: Context[Service], uri: str) -> CallToolResult:
    """Read an ale:// resource for clients that do not expose native resources to the model.

    Uses exactly the same permissions and limits as resources/read. Text uses UTF-8 byte
    offset/limit queries and returns next_offset; lists use item offset/limit.
    Append ?offset=0&limit=4096 for a text chunk. Images return one bounded image.
    Reading never generates cases, evaluates code, or generates evaluation visualizations.
    """
    result = service(ctx).read(uri)
    if isinstance(result, bytes):
        return CallToolResult(content=[Image(data=result, format="webp").to_image_content()])
    return reply(result)


# Register binary templates before the broader JSON views.
@mcp.resource("ale://problems/{id}/images/{index}", mime_type="image/webp")
@client_errors(resource=True)
async def problem_image(ctx: Context[Service], id: str, index: str) -> str | bytes:
    """Read one statement image listed in the problem's /images index."""
    return native(service(ctx).read(f"ale://problems/{quote(id, safe='')}/images/{index}"))


@mcp.resource("ale://sessions/{id}/evaluations/{job_id}/cases/{index}/visualization", mime_type="image/webp")
@client_errors(resource=True)
async def evaluation_image(ctx: Context[Service], id: str, job_id: str, index: str) -> str | bytes:
    """Read a previously generated evaluation image; never generate on read."""
    return native(service(ctx).read(f"ale://sessions/{id}/evaluations/{job_id}/cases/{index}/visualization"))


@mcp.resource("ale://problems{?offset,limit}", mime_type="application/json")
@client_errors(resource=True)
async def problem_index(ctx: Context[Service], offset: str = "0", limit: str | None = None) -> str | bytes:
    """List available problem IDs with item-based pagination."""
    return native(service(ctx).read(uri_with_query("ale://problems", offset, limit)))


@mcp.resource("ale://sessions{?offset,limit}", mime_type="application/json")
@client_errors(resource=True)
async def session_index(ctx: Context[Service], offset: str = "0", limit: str | None = None) -> str | bytes:
    """List active sessions and their status links with item-based pagination."""
    return native(service(ctx).read(uri_with_query("ale://sessions", offset, limit)))


@mcp.resource("ale://problems/{id}/{+path}{?offset,limit}", mime_type="application/json")
@client_errors(resource=True)
async def problem_resource(
    ctx: Context[Service],
    id: str,
    path: str,
    offset: str = "0",
    limit: str | None = None,
) -> str | bytes:
    """Read metadata, statement/statement_ja, example/input, example/output, public_seeds, tools, or images.

    tools lists allowlisted Rust source/manifest/README URIs. Text responses contain text,
    total_bytes and next_offset; lists contain items, total and next_offset.
    """
    return native(service(ctx).read(uri_with_query(f"ale://problems/{quote(id, safe='')}/{path}", offset, limit)))


@mcp.resource("ale://sessions/{id}/{+path}{?offset,limit}", mime_type="application/json")
@client_errors(resource=True)
async def session_resource(
    ctx: Context[Service],
    id: str,
    path: str,
    offset: str = "0",
    limit: str | None = None,
) -> str | bytes:
    """Read status, evaluations, case_sets, or runs and their selected details.

    Evaluation/case-set summary: {collection}/{job_id}; case index: .../cases;
    case metadata: .../cases/{index}; text: .../cases/{index}/input|output|stderr|message.
    Raw code runs expose .../runs/{job_id}/stdin|stdout|stderr. action_log is never exposed.
    """
    result = service(ctx).read(uri_with_query(f"ale://sessions/{id}/{path}", offset, limit))
    if isinstance(result, bytes):
        msg = "Image resource URIs do not accept query parameters; remove the query to read the image."
        raise ResourceError(msg)
    return native(result)


@mcp.resource("ale://{entry}", mime_type="application/json")
@client_errors(resource=True)
async def app_resource(ctx: Context[Service], entry: str) -> str | bytes:
    """Read server entry points and operator-configured storage/retrieval limits."""
    return native(service(ctx).read(f"ale://{entry}"))
