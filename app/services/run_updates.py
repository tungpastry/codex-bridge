from __future__ import annotations

from app.core.settings import Settings
from app.schemas.execution import ExecutionCallbackRequest
from app.services.run_index import get_run_index
from app.utils.files import iso_now


def apply_execution_callback(settings: Settings, run_id: str, payload: ExecutionCallbackRequest) -> None:
    repository = get_run_index(settings)
    status = payload.status
    update_fields = {
        "status": status,
        "finished_at": payload.timing.finished_at or iso_now(),
        "blocked_flag": 1 if status == "blocked" else 0,
        "timeout_flag": 1 if payload.timeout_flag or status == "timeout" else 0,
        "interrupted_flag": 1 if payload.interrupted_flag or status == "interrupted" else 0,
        "needs_human_flag": 1 if payload.needs_human or status == "blocked" else 0,
        "block_reason": payload.block_reason or payload.why,
        "timing_total_ms": payload.timing.total_duration_ms,
        "timing_model_ms": payload.timing.gemini_cli_duration_ms,
        "timing_exec_ms": payload.timing.exec_duration_ms,
        "command_count": len(payload.results),
    }

    artifact_paths = {artifact.artifact_type: artifact.path for artifact in payload.artifacts}
    if artifact_paths.get("final_result"):
        update_fields["final_artifact_path"] = artifact_paths["final_result"]

    repository.update_run(run_id, update_fields)
    repository.upsert_run_commands(
        run_id,
        [result.model_dump() for result in payload.results],
    )
    repository.upsert_artifacts([{"run_id": run_id, **artifact.model_dump()} for artifact in payload.artifacts])
