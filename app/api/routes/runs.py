from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas.runs import RunArtifactsResponse, RunDetailResponse, RunListResponse
from app.services.run_queries import get_run_artifacts, get_run_detail, list_runs

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.get("", response_model=RunListResponse)
async def list_runs_route(
    repo: str = "",
    route: str = "",
    status: str = "",
    date: str = "",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> RunListResponse:
    return list_runs(
        get_settings(),
        repo=repo,
        route=route,
        status=status,
        date=date,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run_route(run_id: str) -> RunDetailResponse:
    response = get_run_detail(get_settings(), run_id)
    if not response:
        raise HTTPException(status_code=404, detail="run_not_found")
    return response


@router.get("/{run_id}/artifacts", response_model=RunArtifactsResponse)
async def get_run_artifacts_route(run_id: str) -> RunArtifactsResponse:
    return get_run_artifacts(get_settings(), run_id)
