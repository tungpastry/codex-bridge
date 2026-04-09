from __future__ import annotations

from typing import List

from pydantic import Field

from app.schemas.common import SchemaBase


class ArtifactMetadata(SchemaBase):
    artifact_type: str
    path: str
    content_type: str = ""
    created_at: str = ""
    size_bytes: int = 0
    sha256: str = ""


class DispatchArtifactsBlock(SchemaBase):
    request_snapshot_path: str = ""
    response_snapshot_path: str = ""
    generated: List[ArtifactMetadata] = Field(default_factory=list)
