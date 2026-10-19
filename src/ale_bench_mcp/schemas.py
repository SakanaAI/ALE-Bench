"""Compact, read-only status returned to MCP clients."""

from datetime import datetime

from pydantic import BaseModel, Field

from ale_bench.result import ResourceUsage


class SessionStatus(BaseModel):
    """Report effective session budgets without private data or unbounded logs."""

    problem_uri: str = Field(description="Problem metadata resource URI; the status id identifies the session.")
    session_started_at: datetime
    session_duration_seconds: float
    remaining_time_seconds: float = Field(description="Remaining wall time; negative after the deadline.")
    session_finished: bool
    finished_reason: str | None
    use_same_time_scale: bool
    maximum_resource_usage: ResourceUsage
    current_resource_usage: ResourceUsage
    remaining_resource_usage: ResourceUsage = Field(description="Maximum minus used; may be negative after an overrun.")
    next_public_eval_time: datetime = Field(
        description="Earliest public evaluation time, subject to remaining budgets."
    )
    reuse_containers: bool
