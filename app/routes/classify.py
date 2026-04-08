from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.task import TaskClassificationRequest, TaskClassificationResponse
from app.services.task_router import classify_task
from app.utils.files import save_json_snapshot

router = APIRouter(prefix="/v1/classify", tags=["classify"])


@router.post("/task", response_model=TaskClassificationResponse)
async def classify_task_route(request: TaskClassificationRequest) -> TaskClassificationResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "classify-task", request.model_dump())
    response = classify_task(request)
    save_json_snapshot(settings.storage_dir, "responses", "classify-task", response.model_dump())
    return response
