"""Operator-owned settings read once when the MCP server starts."""

import os

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServerConfig(BaseModel):
    """Configure sessions without exposing budget controls as tool arguments."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    max_sessions: int = Field(
        default=5,
        ge=1,
        description="Maximum live sessions per server process; only one session per problem is allowed.",
    )
    num_workers: int = Field(
        default=10, ge=1, description="Judge workers within an evaluation; MCP tool calls still execute serially."
    )
    lite_version: bool = Field(default=False, description="Use the ALE-Bench lite problem set and reduced case sets.")
    use_same_time_scale: bool = Field(
        default=False,
        description=(
            "Enforce contest submission intervals and derive the public-evaluation call budget from contest metadata."
        ),
    )
    maximum_num_case_gen: int = Field(
        default=10**18,
        ge=0,
        description="Per-session generated-case budget; the core default of 10**18 is effectively unlimited.",
    )
    maximum_num_case_eval: int = Field(
        default=10**18, ge=0, description="Per-session evaluated-case budget, accounted for by ALE-Bench core."
    )
    maximum_execution_time_case_eval: float = Field(
        default=1e18,
        ge=0,
        description="Per-session cumulative case execution-time budget in seconds; not a per-call wall-clock timeout.",
    )
    maximum_num_call_public_eval: int = Field(
        default=10**18,
        ge=0,
        description="Per-session public-evaluation call budget; ignored when use_same_time_scale is true.",
    )
    session_duration_seconds: float | None = Field(
        default=None, gt=0, description="Session duration in seconds; None uses the problem's contest duration."
    )
    run_visualization_server: bool = Field(
        default=True,
        description="Enable the core browser visualization server; independent of MCP image-resource generation.",
    )
    reuse_containers: bool = Field(
        default=True, description="Reuse judge containers across cases within an evaluation to reduce startup overhead."
    )

    storage_directory: str | None = Field(
        default=None,
        description=(
            "Existing parent for a process-owned temporary artifact directory; "
            "None uses the system temporary directory."
        ),
    )
    max_storage_bytes: int = Field(
        default=1024 * 1024 * 1024,
        ge=16384,
        description=(
            "Per-process logical artifact byte quota, including 4096 bytes per summary and 256 per blob index entry. "
            "Excludes Docker storage, dataset caches, and live objects; details are evicted under capacity pressure."
        ),
    )
    max_artifacts: int = Field(
        default=1024,
        ge=1,
        description="Maximum retained operation summaries/index entries across all sessions in the process.",
    )
    retention_seconds: float = Field(
        default=3600,
        gt=0,
        description=(
            "Artifact lifetime in seconds from operation completion; reads do not extend it. "
            "Expiry is checked on access/operations, with remaining files removed on normal shutdown."
        ),
    )
    max_read_bytes: int = Field(
        default=1024 * 1024,
        ge=4096,
        description=(
            "Maximum serialized resource-read payload or decoded image size in bytes; not the JSON-RPC envelope size."
        ),
    )
    default_read_bytes: int = Field(
        default=65536,
        ge=4,
        description="Default UTF-8 text chunk size in bytes when no limit is supplied; must not exceed max_read_bytes.",
    )
    max_page_items: int = Field(
        default=100, ge=1, description="Maximum and default items per resource list page; max_read_bytes also applies."
    )

    @model_validator(mode="after")
    def validate_read_limits(self) -> "ServerConfig":
        """Ensure the default text chunk fits the maximum read size."""
        if self.default_read_bytes > self.max_read_bytes:
            msg = "DEFAULT_READ_BYTES must not exceed MAX_READ_BYTES."
            raise ValueError(msg)
        return self

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Read ALE_BENCH_MCP_<FIELD_NAME> settings, rejecting invalid values."""
        values = {}
        for name in cls.model_fields:
            value = os.getenv(f"ALE_BENCH_MCP_{name.upper()}")
            if value is not None:
                values[name] = value
        return cls.model_validate(values)
