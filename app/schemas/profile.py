from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.common import SchemaBase


class ProfileDefinition(SchemaBase):
    repo_name: str
    default_safe_services: List[str] = Field(default_factory=list)
    common_repo_paths: List[str] = Field(default_factory=list)
    common_likely_files: List[str] = Field(default_factory=list)
    prompt_hints: List[str] = Field(default_factory=list)
