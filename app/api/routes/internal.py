from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.schemas.execution import ExecutionCallbackRequest
from app.services.run_updates import apply_execution_callback

router = APIRouter(prefix="/v1/internal", tags=["internal"])


@router.post("/runs/{run_id}/execution")
async def update_run_execution_route(
    run_id: str,
    payload: ExecutionCallbackRequest,
    x_codex_bridge_token: str = Header(default=""),
) -> dict[str, str]:
    settings = get_settings()
    if x_codex_bridge_token != settings.internal_api_token:
        raise HTTPException(status_code=401, detail="invalid_internal_token")
    apply_execution_callback(settings, run_id, payload)
    return {"status": "ok", "run_id": run_id}
