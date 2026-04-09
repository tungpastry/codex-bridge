from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.runs import MetricsResponse
from app.services.run_queries import get_admin_metrics

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/metrics", response_model=MetricsResponse)
async def metrics_route() -> MetricsResponse:
    return get_admin_metrics(get_settings())
