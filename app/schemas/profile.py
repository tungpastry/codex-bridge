from __future__ import annotations

from typing import Dict, List

from pydantic import Field

from app.schemas.common import SchemaBase
from app.schemas.gemini_job import AllowedHost


class ProfileDefinition(SchemaBase):
    repo_name: str
    default_safe_services: List[str] = Field(default_factory=list)
    common_repo_paths: List[str] = Field(default_factory=list)
    common_likely_files: List[str] = Field(default_factory=list)
    preferred_command_hosts: Dict[str, AllowedHost] = Field(default_factory=dict)
    prompt_hints: List[str] = Field(default_factory=list)
