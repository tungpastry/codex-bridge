from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.compress import CompressContextRequest, CompressContextResponse
from app.services.prompt_compressor import compress_context
from app.utils.files import save_json_snapshot

router = APIRouter(prefix="/v1/compress", tags=["compress"])


@router.post("/context", response_model=CompressContextResponse)
async def compress_context_route(request: CompressContextRequest) -> CompressContextResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "compress-context", request.model_dump())
    response = compress_context(request)
    save_json_snapshot(settings.storage_dir, "responses", "compress-context", response.model_dump())
    return response
