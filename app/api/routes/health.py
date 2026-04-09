from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.config import get_settings
from app.execution.validator import ALLOWED_HOSTS, allowed_command_ids
from app.index.manager import current_user_version
from app.utils.files import iso_now

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    request: Request,
    depth: str = Query(default="basic"),
) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = {
        "status": "ok",
        "service": settings.app_name,
        "llm_backend": settings.llm_backend,
        "model": settings.llm_model,
        "time": iso_now(),
    }
    if depth != "full":
        return payload

    runtime = getattr(request.app.state, "runtime", None)
    payload.update(
        {
            "depth": "full",
            "index": {
                "status": "ok" if settings.run_index_db_path.exists() else "missing",
                "db_path": str(settings.run_index_db_path),
                "user_version": current_user_version(settings.run_index_db_path),
            },
            "storage_dir": str(settings.storage_dir),
            "profiles": {
                "count": len(runtime.profile_names) if runtime else 0,
                "names": runtime.profile_names if runtime else [],
            },
            "execution": {
                "allowed_hosts": list(ALLOWED_HOSTS),
                "allowed_command_count": len(allowed_command_ids()),
            },
        }
    )
    return payload
