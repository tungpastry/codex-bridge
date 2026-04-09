from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field

from app.schemas.artifact import ArtifactMetadata
from app.schemas.common import SchemaBase


class RunSummary(SchemaBase):
    run_id: str
    job_id: str | None = None
    created_at: str
    finished_at: str | None = None
    status: str
    route: str
    input_kind: str
    repo: str | None = None
    profile_name: str | None = None
    title: str
    task_type: str
    severity: str
    problem_summary: str | None = None
    next_step: str | None = None
    blocked_flag: int = 0
    timeout_flag: int = 0
    interrupted_flag: int = 0
    needs_human_flag: int = 0
    timing_total_ms: int = 0
    timing_model_ms: int = 0
    timing_exec_ms: int = 0
    command_count: int = 0


class RunListResponse(SchemaBase):
    items: List[RunSummary] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class RunDetailResponse(SchemaBase):
    run: Dict[str, Any]
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    commands: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[ArtifactMetadata] = Field(default_factory=list)


class RunArtifactsResponse(SchemaBase):
    run_id: str
    items: List[ArtifactMetadata] = Field(default_factory=list)


class MetricsResponse(SchemaBase):
    runs_total: int = 0
    runs_today: int = 0
    blocked_today: int = 0
    timeouts_today: int = 0
    route_distribution: Dict[str, int] = Field(default_factory=dict)
    average_timing_ms: Dict[str, int] = Field(default_factory=dict)
