from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.log_summary import LogSummaryRequest, LogSummaryResponse
from app.services.log_triage import summarize_log
from app.utils.files import save_json_snapshot

router = APIRouter(prefix="/v1/summarize", tags=["logs"])


@router.post("/log", response_model=LogSummaryResponse)
async def summarize_log_route(request: LogSummaryRequest) -> LogSummaryResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "summarize-log", request.model_dump())
    response = summarize_log(request)
    save_json_snapshot(settings.storage_dir, "responses", "summarize-log", response.model_dump())
    return response
