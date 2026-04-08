from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.utils.files import iso_now

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "llm_backend": settings.llm_backend,
        "model": settings.llm_model,
        "time": iso_now(),
    }
