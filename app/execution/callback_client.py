from __future__ import annotations

from pathlib import Path

import httpx

from app.artifacts.registry import build_artifact_record
from app.schemas.execution import ExecutionBatchResult, ExecutionCallbackRequest


def build_callback_payload(
    *,
    run_id: str,
    final_payload: dict,
    artifact_files: list[tuple[str, str | Path]],
) -> ExecutionCallbackRequest:
    artifacts = [
        build_artifact_record(run_id, artifact_type, path)
        for artifact_type, path in artifact_files
        if path and Path(path).exists()
    ]
    payload = ExecutionCallbackRequest.model_validate(
        {
            "phase": final_payload.get("phase", "final"),
            "status": final_payload.get("status", "failed"),
            "summary": final_payload.get("summary", ""),
            "confidence": final_payload.get("confidence", ""),
            "why": final_payload.get("why", ""),
            "final_markdown": final_payload.get("final_markdown", ""),
            "block_reason": final_payload.get("block_reason", "") or final_payload.get("reason", ""),
            "needs_human": final_payload.get("needs_human", False) or final_payload.get("status") == "blocked",
            "timeout_flag": final_payload.get("timeout_flag", False),
            "interrupted_flag": final_payload.get("interrupted_flag", False),
            "timing": final_payload.get("timing", {}),
            "results": final_payload.get("results", []),
            "artifacts": artifacts,
        }
    )
    return payload


def post_execution_callback(
    *,
    base_url: str,
    run_id: str,
    token: str,
    payload: ExecutionCallbackRequest,
) -> None:
    if not base_url or not token or not run_id:
        return
    url = base_url.rstrip("/") + f"/v1/internal/runs/{run_id}/execution"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            json=payload.model_dump(),
            headers={"X-Codex-Bridge-Token": token},
        )
        response.raise_for_status()
