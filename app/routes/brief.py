from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.codex_brief import CodexBriefRequest, CodexBriefResponse
from app.services.codex_brief_builder import build_codex_brief
from app.utils.files import save_json_snapshot, save_text_snapshot

router = APIRouter(prefix="/v1/brief", tags=["brief"])


@router.post("/codex", response_model=CodexBriefResponse)
async def build_codex_brief_route(request: CodexBriefRequest) -> CodexBriefResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "brief-codex", request.model_dump())
    response = build_codex_brief(request)
    save_json_snapshot(settings.storage_dir, "responses", "brief-codex", response.model_dump())
    save_text_snapshot(settings.storage_dir, "reports", "codex-brief", response.brief_markdown)
    return response
