from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.report import DailyReportRequest, DailyReportResponse
from app.services.report_builder import build_daily_report
from app.utils.files import save_json_snapshot, save_text_snapshot

router = APIRouter(prefix="/v1/report", tags=["report"])


@router.post("/daily", response_model=DailyReportResponse)
async def build_daily_report_route(request: DailyReportRequest) -> DailyReportResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "report-daily", request.model_dump())
    response = build_daily_report(request)
    save_json_snapshot(settings.storage_dir, "responses", "report-daily", response.model_dump())
    save_text_snapshot(settings.storage_dir, "reports", "daily-report", response.markdown)
    return response
