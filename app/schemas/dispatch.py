from __future__ import annotations

from typing import Literal, Optional, List

from pydantic import Field

from app.schemas.common import SchemaBase
from app.schemas.gemini_job import GeminiJob


InputKind = Literal["task", "log", "diff", "report"]
RouteTarget = Literal["codex", "gemini", "human", "local"]


class DispatchTaskRequest(SchemaBase):
    title: str
    input_kind: InputKind
    context: str
    repo: str = ""
    source: str = "manual"
    constraints: List[str] = Field(default_factory=list)
    target_host: str = ""


class DispatchTaskResponse(SchemaBase):
    route: RouteTarget
    task_type: str
    severity: str
    problem_summary: str
    next_step: str
    codex_brief_markdown: Optional[str] = None
    gemini_job: Optional[GeminiJob] = None
    human_summary: Optional[str] = None
    block_reason: Optional[str] = None
    local_summary: Optional[str] = None
