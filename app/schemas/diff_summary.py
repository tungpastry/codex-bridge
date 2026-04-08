from __future__ import annotations

from typing import List, Literal

from pydantic import Field

from app.schemas.common import SchemaBase


RiskLevel = Literal["low", "medium", "high"]
RecommendedTool = Literal["local", "gemini", "codex", "human"]


class DiffSummaryRequest(SchemaBase):
    repo: str
    diff_text: str
    base_ref: str = "main"
    head_ref: str = "HEAD"
    context: str = ""


class DiffSummaryResponse(SchemaBase):
    summary: str
    risk_level: RiskLevel
    risk_flags: List[str] = Field(default_factory=list)
    review_focus: List[str] = Field(default_factory=list)
    recommended_tool: RecommendedTool
    next_step: str
