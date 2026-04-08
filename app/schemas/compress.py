from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.common import SchemaBase


class CompressContextRequest(SchemaBase):
    title: str
    context: str
    repo: str = ""
    constraints: List[str] = Field(default_factory=list)
    target_tool: str = ""


class CompressContextResponse(SchemaBase):
    compressed_context: str
    key_points: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
