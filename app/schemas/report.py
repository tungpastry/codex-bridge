from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.common import SchemaBase


class DailyReportRequest(SchemaBase):
    repo: str = ""
    items: List[str] = Field(default_factory=list)
    raw_text: str = ""
    context: str = ""
    source: str = "manual"


class DailyReportResponse(SchemaBase):
    markdown: str
    done: List[str] = Field(default_factory=list)
    open_issues: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
