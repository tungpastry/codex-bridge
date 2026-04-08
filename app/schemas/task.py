from __future__ import annotations

from typing import List, Literal

from pydantic import Field

from app.schemas.common import SchemaBase


TaskType = Literal["bugfix", "ops", "setup", "review", "deploy", "research", "feature", "unknown"]
Severity = Literal["low", "medium", "high", "critical"]
RecommendedTool = Literal["local", "gemini", "codex", "human"]


class TaskClassificationRequest(SchemaBase):
    title: str
    context: str
    repo: str = ""
    source: str = "manual"
    constraints: List[str] = Field(default_factory=list)


class TaskClassificationResponse(SchemaBase):
    task_type: TaskType
    severity: Severity
    repo: str
    problem_summary: str
    signals: List[str] = Field(default_factory=list)
    suspected_files: List[str] = Field(default_factory=list)
    recommended_tool: RecommendedTool
    next_step: str
