from __future__ import annotations

from app.core.settings import Settings
from app.schemas.runs import MetricsResponse, RunArtifactsResponse, RunDetailResponse, RunListResponse, RunSummary
from app.services.run_index import get_run_index
from app.utils.files import iso_now


def list_runs(
    settings: Settings,
    *,
    repo: str = "",
    route: str = "",
    status: str = "",
    date: str = "",
    limit: int = 50,
    offset: int = 0,
) -> RunListResponse:
    payload = get_run_index(settings).list_runs(
        repo=repo,
        route=route,
        status=status,
        date=date,
        limit=limit,
        offset=offset,
    )
    return RunListResponse(
        items=[RunSummary.model_validate(item) for item in payload["items"]],
        total=payload["total"],
        limit=payload["limit"],
        offset=payload["offset"],
    )


def get_run_detail(settings: Settings, run_id: str) -> RunDetailResponse | None:
    repository = get_run_index(settings)
    run = repository.get_run(run_id)
    if not run:
        return None
    return RunDetailResponse(
        run=run,
        rules=repository.get_run_rules(run_id),
        commands=repository.get_run_commands(run_id),
        artifacts=repository.get_artifacts(run_id),
    )


def get_run_artifacts(settings: Settings, run_id: str) -> RunArtifactsResponse:
    return RunArtifactsResponse(
        run_id=run_id,
        items=get_run_index(settings).get_artifacts(run_id),
    )


def get_admin_metrics(settings: Settings) -> MetricsResponse:
    date = iso_now()[:10]
    return MetricsResponse.model_validate(get_run_index(settings).metrics(date=date))
