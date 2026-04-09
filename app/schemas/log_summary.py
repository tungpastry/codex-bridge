from __future__ import annotations

from typing import List, Literal

from pydantic import Field

from app.schemas.common import SchemaBase
from app.schemas.decision_trace import DecisionTrace


RecommendedTool = Literal["local", "gemini", "codex", "human"]


class LogSummaryRequest(SchemaBase):
    service: str = ""
    log_text: str
    repo: str = ""
    context: str = ""
    source: str = "manual"
    host: str = ""


class LogSummaryResponse(SchemaBase):
    symptom: str
    likely_cause: str
    important_lines: List[str] = Field(default_factory=list)
    recommended_commands: List[str] = Field(default_factory=list)
    needs_codex: bool = False
    recommended_tool: RecommendedTool
    next_step: str
    decision_trace: DecisionTrace = Field(default_factory=DecisionTrace)
