# MCP (Model Context Protocol) Server
The MCP server uses the official MCP Python SDK v2 and communicates over stdio. It provides a simple interface for interacting with the ALE-Bench toolkit. It allows you to run evaluations and manage sessions without needing to write Python code directly.

## Setup

Follow the [ALE-Bench installation prerequisites](../README.md#setup), including Cairo and the Docker setup needed for evaluations.

Docker Hub images such as `yimjk/ale-bench:cpp20-202301` are base images. Build the local execution images with your user/group IDs; pulling or retagging a base image alone does not set the required write permissions. For example, from the repository root, to prepare only C++20 for judge version `202301`:

```sh
docker build ./dockerfiles -t ale-bench:cpp20-202301 \
  -f ./dockerfiles/Dockerfile_cpp20_202301 \
  --build-arg UID="$(id -u)" --build-arg GID="$(id -g)"
```

The README's build scripts prepare all languages for a judge version. Run them as the same user that launches the MCP server.

Install ALE-Bench with the MCP extra:

```sh
pip install 'ale-bench[mcp]'
ale-bench-mcp
```

To run only the MCP server from a checkout, use the repository root:

```sh
uv sync --locked --extra mcp
uv run --locked --extra mcp ale-bench-mcp
```

## Running the MCP Server

The server communicates over stdio. These commands are equivalent from a checkout:

```sh
uv run --locked --extra mcp ale-bench-mcp
uv run --locked --extra mcp python -m ale_bench_mcp
```

Node.js/npm is needed only for the optional MCP Inspector UI:

```sh
npx @modelcontextprotocol/inspector uv run --locked --extra mcp ale-bench-mcp
```

The former `mcp/` directory has been removed. Update existing client configurations
to use the repository root with `--extra mcp` and the `ale-bench-mcp` entry point.

## Use with Claude Desktop
1. Open the `claude_desktop_config.json` file that configures the Claude Desktop. Add the following configuration to connect to the MCP server, ensuring you replace `/path/to/ALE-Bench` in the `args` with the actual absolute path to your cloned `ALE-Bench` repository directory:
    ```json
    {
        "mcpServers": {
            "ALE-Bench MCP Server": {
                "command": "uv",
                "args": [
                    "run",
                    "--project",
                    "/path/to/ALE-Bench",
                    "--locked",
                    "--extra",
                    "mcp",
                    "ale-bench-mcp"
                ]
            }
        }
    }
    ```
   Use the absolute path to `uv` for `command` if it is not on the desktop application's PATH.
2. Restart the Claude Desktop application to apply the changes.

<img width="680" alt="MCP_Claude_Desktop" src="https://github.com/user-attachments/assets/d9f22719-5686-406d-aa94-44406c700d6f" />

## Resource-oriented API

This API replaces the previous per-method tools; there is no backwards-compatibility layer for tool names or result shapes. The launch commands above remain supported. All benchmark operations are synchronous: other requests, including resource reads, wait until an evaluation finishes. The core ALE-Bench session owns generation, evaluation, visualization, and budget checks. MCP owns bounded result retention and views.

### Tools

| Tool | Purpose |
| --- | --- |
| `start_session(id)` | Start the specified problem; return a new session `id` and links to status, problem metadata, statement, and Rust sources |
| `close_session(id)` | Release the live session; saved artifacts remain until expiry/eviction |
| `generate_cases(id, seed, gen_kwargs)` | Generate once; return a stored case-set `job_id` and resource URI |
| `evaluate(id, target, code, code_language, job_id, ...)` | Evaluate once; return a new evaluation `job_id`, scores, usage, availability, and a resource URI |
| `code_run(id, input_str, code, code_language, ...)` | Run code; return a new `job_id`, execution statistics, and a resource URI for stdin/stdout/stderr |
| `visualize_case(id, job_id, case_index)` | Generate/cache one image from retained evaluation inputs/outputs, without rerunning code |
| `read_resource(uri)` | Read the same bounded resource as native `resources/read`, including images |

The input `id` of `start_session` is a **problem ID** from `ale://problems`. Its returned `id` is a new **session ID**: use that value for every subsequent session-scoped tool call. Active session IDs are also listed at `ale://sessions`; they belong to the current MCP server process and cannot be reused after restarting it. Problem metadata exposes the problem's `id`; session responses and status expose the session's `id` and link to the problem through `problem_uri`.

The public tool field is named `id`, which also avoids collisions with client metadata such as Claude Desktop's `session_id`.

`evaluate.target` selects the core operation:

- `cases`: provide exactly one of `input_str` (one string or a list) or `job_id` from `generate_cases` in the same session. An evaluation or code-run job cannot be used as a case set. The response contains a new evaluation `job_id`, distinct from the input case-set `job_id`.
- `generated`: provide `seed` (one integer or a list, default `0`) and optional `gen_kwargs`. Delegates to core `case_gen_eval`, including both budget checks.
- `public` / `private`: use benchmark-defined cases and limits. Custom inputs, generation options, `time_limit`, and `memory_limit` are rejected.

All targets accept `judge_version`. Local targets and `code_run` also accept `time_limit` and `memory_limit`. Container reuse is an operator setting, not a tool argument. Private evaluation remains one-shot and returns rank/performance alongside redacted scores/statistics. It never publishes private inputs, outputs, stderr, messages, or images.

Operation responses contain `structuredContent` plus a native MCP resource link. Each generation, evaluation, or code run returns its session `id`, a unique `job_id`, and a `kind` (`case_sets`, `evaluations`, or `runs`). One generation job can contain multiple cases, selected by `case_index`. A job represents one synchronous operation; it is not an asynchronous task. Pass a generation `job_id` to `evaluate(target="cases", ...)`, or an evaluation `job_id` to `visualize_case`. Visualization returns the source evaluation's `job_id` and creates no new job. The server validates both session ownership and job kind.

`details_available=false` means the operation **completed** but its detailed output could not be retained. The score/summary is still returned; do not blindly retry a budget-consuming operation to recover its details.

### Resources

Resource templates are discoverable through `resources/templates/list`. Start with `ale://app` for entry points and configured limits. Problem resources require an active session for that problem; they are released when it closes. Session IDs are unique across restarts of the same problem, so old result URIs never point to a new run.

| URI | Content |
| --- | --- |
| `ale://app` | Server information and storage/read limits |
| `ale://problems` | Available problem IDs |
| `ale://problems/{id}/metadata` | Problem metadata and constraints |
| `ale://problems/{id}/statement` | English statement as a text chunk |
| `ale://problems/{id}/statement_ja` | Japanese statement as a text chunk |
| `ale://problems/{id}/images` | Statement image names/frames and individual image URIs |
| `ale://problems/{id}/images/{index}` | One statement image, WebP |
| `ale://problems/{id}/example/input` or `/example/output` | Example text |
| `ale://problems/{id}/public_seeds` | Public seed list |
| `ale://problems/{id}/tools` | Allowlisted public Rust files and README resource URIs |
| `ale://problems/{id}/tools/src/bin/gen.rs` | Example individual source file; use the `/tools` index for actual paths |
| `ale://sessions` | Active session IDs and status URIs |
| `ale://sessions/{id}/status` | Effective budgets, usage, remaining time, cooldown, and visualization server port |
| `ale://sessions/{id}/{collection}` | Retained operation summaries; collection is `evaluations`, `case_sets`, or `runs` |
| `ale://sessions/{id}/{collection}/{job_id}` | One operation summary and current detail availability |
| `.../evaluations/{job_id}/cases` or `.../case_sets/{job_id}/cases` | Case index and metadata links |
| `.../evaluations/{job_id}/cases/{index}` | Case scores, timing, memory, and available text field names |
| `.../evaluations/{job_id}/cases/{index}/input`, `/output`, `/stderr`, `/message` | Selected text field of a non-private evaluation |
| `.../case_sets/{job_id}/cases/{index}/input` | Generated input |
| `.../evaluations/{job_id}/cases/{index}/visualization` | Previously generated image; reading never generates it |
| `.../runs/{job_id}/stdin`, `/stdout`, `/stderr` | Raw code execution text |

The Rust index exposes `.rs` files under the problem's Rust source directory, `Cargo.toml`, and the public tools README. It does not expose arbitrary filesystem paths, symlinks to outside files, or the benchmark's internal data directory. Clients do not need filesystem access to the server. Sources are not automatically exported into a client working directory.

`action_log` is never exposed. Status remains readable after the deadline or private evaluation, until `close_session`. Negative remaining values indicate an overrun; exhausting a local/public budget does not necessarily finish the entire session.

### Bounded reads

Text resources return JSON with `text`, `offset`, `total_bytes`, and `next_offset`. `offset` and `limit` are UTF-8 **byte** counts; use the returned `next_offset` to avoid splitting a multibyte character. Lists return `items`, `total`, and `next_offset`; for lists, offset/limit count **items**. Pass query parameters in either native reads
or the `read_resource` tool:

```text
ale://problems/ahc001/statement?offset=0&limit=4096
ale://problems/ahc001/tools/src/bin/gen.rs?offset=4096&limit=4096
ale://sessions/{id}/evaluations/{job_id}/cases?offset=0&limit=20
```

JSON metadata/summary resources are returned whole, subject to the read-byte limit. Images are returned one at a time and do not support ranges. The byte limit applies to serialized JSON/text payloads or decoded image bytes; MCP envelopes, the duplicate structured/text tool representation, and base64 encoding add wire overhead. JSON escaping can expand text: if a chunk exceeds the serialized limit, request a smaller `limit`. Very large images are rejected with an operator-facing limit message.

### Typical workflow

1. Read `ale://problems`, then call `start_session(id="ahc001")` and retain the returned session `id`.
2. Read the returned statement and tools URIs; select individual Rust files or images.
3. Call `generate_cases(id=..., seed=[0, 1, 2])` and retain its `job_id`.
4. Call `evaluate(id=..., target="cases", job_id=..., code=..., code_language="cpp20")` with the generation `job_id`; retain the new evaluation `job_id` from its response.
5. Inspect the short score summary, then read selected case metadata/output resources.
6. Call `visualize_case(id=..., job_id=..., case_index=0)` with the evaluation `job_id` for one interesting case, then read the returned image URI.
7. Call `evaluate(id=..., target="private", ...)` without an input `job_id` for the final submission, then call `close_session(id=...)`.

The first visualization call requires a live, unfinished session because it uses the core `Session.local_visualization`. Once cached, its image remains readable after session close until artifact expiry/eviction. Reading an image never re-evaluates code. Automatic bulk image generation and bulk image responses are intentionally absent.

## Server configuration

Environment variables are validated at startup and fixed for the server's lifetime. No tool/resource changes the configuration. All names have the prefix `ALE_BENCH_MCP_`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `MAX_SESSIONS` | `5` | Maximum live sessions; at most one active session per problem |
| `NUM_WORKERS` | `10` | Workers inside an evaluation, not simultaneous tool calls |
| `LITE_VERSION` | `false` | Use the lite dataset |
| `USE_SAME_TIME_SCALE` | `false` | Apply benchmark submission intervals and the derived public-call limit |
| `MAXIMUM_NUM_CASE_GEN` | `1000000000000000000` | Per-session generated-case budget |
| `MAXIMUM_NUM_CASE_EVAL` | `1000000000000000000` | Per-session evaluated-case budget |
| `MAXIMUM_EXECUTION_TIME_CASE_EVAL` | `1e18` | Case evaluation execution-time budget in seconds |
| `MAXIMUM_NUM_CALL_PUBLIC_EVAL` | `1000000000000000000` | Public-call budget when `USE_SAME_TIME_SCALE=false` |
| `SESSION_DURATION_SECONDS` | unset | Session duration; unset uses the contest duration |
| `RUN_VISUALIZATION_SERVER` | `true` | Start the existing browser visualization server |
| `REUSE_CONTAINERS` | `true` | Reuse containers across cases within an evaluation |
| `STORAGE_DIRECTORY` | system temporary directory | Existing parent directory for an exclusively owned temporary subdirectory |
| `MAX_STORAGE_BYTES` | `1073741824` (1 GiB) | Detail bytes plus 4096 bytes per summary and 256 bytes per blob index entry; minimum 16384 |
| `MAX_ARTIFACTS` | `1024` | Maximum retained operation summaries/index entries |
| `RETENTION_SECONDS` | `3600` | Artifact lifetime from operation completion; reading does not extend it |
| `MAX_READ_BYTES` | `1048576` (1 MiB) | Maximum serialized read payload / decoded image bytes; minimum 4096 |
| `DEFAULT_READ_BYTES` | `65536` (64 KiB) | Default text chunk; must be at most `MAX_READ_BYTES` |
| `MAX_PAGE_ITEMS` | `100` | Maximum/default number of items per list page |

Boolean values accept `true`/`false` or `1`/`0`. Counts must be positive except evaluation budgets, which may be zero. Explicit durations/retention must be positive and finite. With `USE_SAME_TIME_SCALE=true`, the core derives the public-call limit from contest duration/submission interval instead of using `MAXIMUM_NUM_CALL_PUBLIC_EVAL`. Read the status resource for effective limits. Budgets are per session: closing and starting again creates a fresh budget, as before.

Defaults are fixed in `ServerConfig`; they are not calculated from CPU count, free disk space, or model context size. The dataset/time-scale switches, effectively unlimited `1e18` budgets, and contest-derived session duration follow the core `ale_bench.start` defaults. MCP enables the browser visualization server as the previous adapter did, and enables container reuse to reduce repeated startup work.

The session/worker counts and storage/read limits are operator-tunable starting points, not benchmark-derived capacity guarantees. The 1 GiB/1024-artifact caps bound retained data and index growth; one-hour retention keeps recent results available without retaining them indefinitely. The 64 KiB default text chunk, 1 MiB read ceiling, and 100-item page cap limit individual responses while allowing explicit reads of larger chunks or images. Choose lower worker counts for smaller hosts and set explicit evaluation budgets for controlled agent runs. All fields carry descriptions in the Pydantic configuration schema.

```sh
ALE_BENCH_MCP_MAXIMUM_NUM_CASE_EVAL=1000 \
ALE_BENCH_MCP_SESSION_DURATION_SECONDS=3600 \
ALE_BENCH_MCP_MAX_STORAGE_BYTES=268435456 \
ALE_BENCH_MCP_RETENTION_SECONDS=1800 \
ALE_BENCH_MCP_MAX_READ_BYTES=262144 \
ALE_BENCH_MCP_DEFAULT_READ_BYTES=16384 \
uv run --locked --extra mcp ale-bench-mcp
```

Desktop clients can set these in the MCP server entry's `env` object.

### Storage lifecycle and errors

- Each process has an isolated temporary directory, removed on normal shutdown. Artifacts are not durable checkpoints and cannot be recovered after restart.
- On capacity pressure, least-recently-accessed artifact **details** are evicted first; summaries report `details_available=false` and `unavailable_reason=evicted...`.
- If a new result cannot fit, all of its details are discarded together and its successful summary reports `storage_limit`. A disk write failure similarly reports `storage_io_error`; it does not pretend that an already completed evaluation failed.
- The summary/index count is also bounded. Old summary entries may be removed to make room for new ones. Missing/evicted IDs never trigger regeneration or evaluation.
- Retention applies to summaries and details, including images. Expiry is checked on access/operations; idle expired files are reclaimed on the next access or shutdown.
- The quota counts logical artifact bytes, including summary and per-blob index reservations, rather than filesystem block allocation. It does not bound Docker storage, the core dataset cache, live result objects, or ALE-Bench's internal in-memory `action_log`.

Errors distinguish unknown/closed sessions, wrong-session artifacts, expired or evicted results, unavailable private fields, invalid ranges, and response/storage limits. Expected `AleBenchError` messages remain visible. Native resource failures use MCP protocol errors; tools return `isError=true` with the same actionable reason. Unexpected implementation exceptions retain the SDK's generic client-facing error.

## Development, versions, and dependencies

`src/ale_bench_mcp/` is included in the `ale-bench` distribution alongside `ale_bench` and `ale_bench_eval`. All three share the root `pyproject.toml`, `uv.lock`, and Git-tag-derived version; there is no separate MCP release or `ale-bench` dependency pin to maintain.

The `[mcp]` extra installs the official MCP Python SDK (`mcp[cli]>=2,<3`). Without this extra, the MCP Python source and entry point are still included in the wheel, but its additional dependencies are not installed. The ordinary `ale_bench` import does not import the MCP server. Like `ale_bench_eval`, `ale_bench_mcp` checks its dependencies in `__init__.py`: importing it without the SDK raises an `ImportError` with installation instructions. Both `ale-bench-mcp` and `python -m ale_bench_mcp` report this same error and share the startup function in `__main__.py`. Other extras or packages can independently bring in the SDK as a dependency.

SDK v2 supports modern and legacy MCP clients. See the [upstream migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md).

For development, install both extras as described in [CONTRIBUTING.md](../CONTRIBUTING.md). From the repository root:

```sh
uv sync --locked --all-extras
uv run --locked --all-extras pytest tests/mcp
uv run --locked --all-extras ruff check
uv run --locked --all-extras ruff format --check
uv run --locked --all-extras ty check
uv build --no-sources
```

MCP client tests live in `tests/mcp/` and skip when the SDK is unavailable. They use fake ALE-Bench sessions and require neither Docker nor benchmark downloads. CI runs them with both extras enabled, and separately checks clean wheel installations for the base package, `[mcp]`, and `[eval]`. Real evaluations require the normal ALE-Bench Docker/data setup.

Client tests exercise modern and legacy protocol modes, native resources and the fallback read tool, public/private result visibility, byte/item limits, UTF-8 ranges, storage eviction/expiry, one-case visualization caching, and synchronous execution. Subprocess tests run real stdio exchanges for evaluation, resource reads, images, and expected/unexpected errors using a fake benchmark backend. Store tests also inject disk write failures. They do not execute real Docker benchmarks.
