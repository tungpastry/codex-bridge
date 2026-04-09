from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.diff_summary import DiffSummaryRequest, DiffSummaryResponse
from app.services.diff_summarizer import summarize_diff
from app.utils.files import save_json_snapshot

router = APIRouter(prefix="/v1/summarize", tags=["diff"])


@router.post("/diff", response_model=DiffSummaryResponse)
async def summarize_diff_route(request: DiffSummaryRequest) -> DiffSummaryResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "summarize-diff", request.model_dump())
    response = summarize_diff(request)
    save_json_snapshot(settings.storage_dir, "responses", "summarize-diff", response.model_dump())
    return response
