from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import Field

from app.schemas.artifact import ArtifactMetadata
from app.schemas.common import SchemaBase


ExecutionStatus = Literal["ok", "blocked", "failed", "timeout", "interrupted"]


class ExecutionCommand(SchemaBase):
    host: str
    command_id: str
    args: Dict[str, object] = Field(default_factory=dict)
    reason: str = ""


class ExecutionPlan(SchemaBase):
    summary: str = ""
    confidence: str = ""
    needs_human: bool = False
    why: str = ""
    commands: List[ExecutionCommand] = Field(default_factory=list)
    final_markdown: str = ""


class ExecutionResult(SchemaBase):
    ordinal: int
    host: str
    command_id: str
    reason: str = ""
    shell_command: str = ""
    status: str
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    truncated_flag: bool = False
    output_path: str = ""


class ExecutionBatchResult(SchemaBase):
    run_id: str
    phase: str = "final"
    status: ExecutionStatus
    summary: str = ""
    confidence: str = ""
    why: str = ""
    final_markdown: str = ""
    needs_human: bool = False
    timeout_flag: bool = False
    interrupted_flag: bool = False
    block_reason: str = ""
    results: List[ExecutionResult] = Field(default_factory=list)


class ExecutionTimingPayload(SchemaBase):
    pipeline_started_at: str | None = None
    gemini_started_at: str | None = None
    gemini_finished_at: str | None = None
    exec_started_at: str | None = None
    exec_finished_at: str | None = None
    finished_at: str | None = None
    gemini_cli_duration_ms: int = 0
    exec_duration_ms: int = 0
    total_duration_ms: int = 0


class ExecutionCallbackRequest(SchemaBase):
    phase: str
    status: ExecutionStatus
    summary: str = ""
    confidence: str = ""
    why: str = ""
    final_markdown: str = ""
    block_reason: str = ""
    needs_human: bool = False
    timeout_flag: bool = False
    interrupted_flag: bool = False
    timing: ExecutionTimingPayload = Field(default_factory=ExecutionTimingPayload)
    results: List[ExecutionResult] = Field(default_factory=list)
    artifacts: List[ArtifactMetadata] = Field(default_factory=list)
