from __future__ import annotations

from typing import List

from app.schemas.compress import CompressContextRequest, CompressContextResponse
from app.utils.text import summarize_block, unique_list


def compress_context(request: CompressContextRequest) -> CompressContextResponse:
    paragraphs = [line.strip("- ").strip() for line in request.context.splitlines() if line.strip()]
    key_points: List[str] = unique_list(paragraphs[:5], limit=5)
    compressed_parts = ["Title: {0}".format(request.title.strip())]
    if request.repo:
        compressed_parts.append("Repo: {0}".format(request.repo.strip()))
    if key_points:
        compressed_parts.append("Context: {0}".format(" | ".join(key_points[:3])))
    if request.constraints:
        compressed_parts.append("Constraints: {0}".format(" | ".join(unique_list(request.constraints, limit=6))))
    if request.target_tool:
        compressed_parts.append("Target Tool: {0}".format(request.target_tool))

    return CompressContextResponse(
        compressed_context=summarize_block(" ; ".join(compressed_parts), limit=420),
        key_points=key_points,
        constraints=unique_list(request.constraints, limit=8),
    )
