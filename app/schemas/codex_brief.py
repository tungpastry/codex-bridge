from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.common import SchemaBase


class CodexBriefRequest(SchemaBase):
    title: str
    repo: str
    context: str
    constraints: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    likely_files: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    task_type: str = ""
    goal: str = ""


class CodexBriefResponse(SchemaBase):
    brief_markdown: str
    task_type: str
    recommended_tool: str = "codex"
