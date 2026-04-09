from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.dispatch import DispatchTaskRequest, DispatchTaskResponse
from app.services.dispatch_service import dispatch_task

router = APIRouter(prefix="/v1/dispatch", tags=["dispatch"])


@router.post("/task", response_model=DispatchTaskResponse)
async def dispatch_task_route(request: DispatchTaskRequest) -> DispatchTaskResponse:
    return dispatch_task(get_settings(), request)
