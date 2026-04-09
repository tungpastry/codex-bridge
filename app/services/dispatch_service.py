from __future__ import annotations

import uuid
from pathlib import Path

from app.artifacts.registry import build_artifact_record
from app.builders.codex_brief import build_codex_brief
from app.builders.daily_report import build_daily_report
from app.builders.gemini_job import build_gemini_job
from app.core.settings import Settings
from app.profiles.loader import load_profiles, resolve_profile
from app.schemas.artifact import ArtifactMetadata, DispatchArtifactsBlock
from app.schemas.codex_brief import CodexBriefRequest
from app.schemas.diff_summary import DiffSummaryRequest
from app.schemas.dispatch import DispatchTaskRequest, DispatchTaskResponse
from app.schemas.log_summary import LogSummaryRequest
from app.schemas.report import DailyReportRequest
from app.schemas.task import TaskClassificationRequest
from app.services.diff_summarizer import summarize_diff
from app.services.log_triage import summarize_log
from app.services.run_index import get_run_index
from app.services.task_router import classify_task
from app.utils.files import iso_now, write_json, write_text


def _run_id() -> str:
    return "run-{0}".format(uuid.uuid4().hex)


def _artifact_path(storage_dir: Path, bucket: str, run_id: str, name: str, extension: str) -> Path:
    return storage_dir / bucket / f"{run_id}-{name}{extension}"


def _persist_request_snapshot(settings: Settings, run_id: str, request: DispatchTaskRequest) -> Path:
    path = _artifact_path(settings.storage_dir, "requests", run_id, "dispatch-request", ".json")
    return write_json(path, request.model_dump())


def _persist_response_snapshot(settings: Settings, run_id: str, response: DispatchTaskResponse) -> Path:
    path = _artifact_path(settings.storage_dir, "responses", run_id, "dispatch-response", ".json")
    return write_json(path, response.model_dump())


def _artifact_metadata(run_id: str, records: list[tuple[str, Path]]) -> list[ArtifactMetadata]:
    return [ArtifactMetadata.model_validate(build_artifact_record(run_id, artifact_type, path)) for artifact_type, path in records]


def dispatch_task(settings: Settings, request: DispatchTaskRequest) -> DispatchTaskResponse:
    run_id = _run_id()
    created_at = iso_now()
    request_snapshot_path = _persist_request_snapshot(settings, run_id, request)
    profiles = load_profiles(settings.profiles_dir)
    profile = resolve_profile(request.repo, profiles)
    profile_name = profile.repo_name if profile else ""
    repository = get_run_index(settings)

    generated_artifacts: list[tuple[str, Path]] = []
    primary_artifact_path = ""

    if request.input_kind == "log":
        log_summary = summarize_log(
            LogSummaryRequest(
                service=request.target_host,
                log_text=request.context,
                repo=request.repo,
                source=request.source,
            )
        )
        decision_trace = log_summary.decision_trace
        if log_summary.recommended_tool == "codex":
            likely_files = profile.common_likely_files if profile else []
            brief = build_codex_brief(
                CodexBriefRequest(
                    title=request.title,
                    repo=request.repo or "MiddayCommander",
                    context="Symptom: {0}\n\nLikely cause: {1}\n\nImportant lines:\n- {2}".format(
                        log_summary.symptom,
                        log_summary.likely_cause,
                        "\n- ".join(log_summary.important_lines),
                    ),
                    constraints=request.constraints,
                    notes=[log_summary.next_step],
                    likely_files=likely_files,
                )
            )
            brief_path = _artifact_path(settings.storage_dir, "reports", run_id, "codex-brief", ".md")
            write_text(brief_path, brief.brief_markdown)
            generated_artifacts.append(("codex_brief", brief_path))
            primary_artifact_path = str(brief_path)
            response = DispatchTaskResponse(
                run_id=run_id,
                route="codex",
                task_type="bugfix",
                severity="high",
                problem_summary=log_summary.symptom,
                next_step=log_summary.next_step,
                codex_brief_markdown=brief.brief_markdown,
                decision_trace=decision_trace,
            )
        elif log_summary.recommended_tool == "human":
            response = DispatchTaskResponse(
                run_id=run_id,
                route="human",
                task_type="ops",
                severity="critical",
                problem_summary=log_summary.symptom,
                next_step=log_summary.next_step,
                human_summary=log_summary.likely_cause,
                block_reason="Risky log pattern requires human review.",
                decision_trace=decision_trace,
            )
        else:
            classification = classify_task(
                TaskClassificationRequest(
                    title=request.title,
                    context=request.context,
                    repo=request.repo,
                    source=request.source,
                    constraints=request.constraints,
                )
            )
            gemini_job = build_gemini_job(settings, request, classification, run_id=run_id, profile=profile)
            gemini_job_path = _artifact_path(settings.storage_dir, "gemini_runs", run_id, "job", ".json")
            write_json(gemini_job_path, gemini_job.model_dump())
            generated_artifacts.append(("gemini_job", gemini_job_path))
            primary_artifact_path = str(gemini_job_path)
            response = DispatchTaskResponse(
                run_id=run_id,
                route="gemini",
                task_type="ops",
                severity="high" if log_summary.recommended_tool == "gemini" else "medium",
                problem_summary=log_summary.symptom,
                next_step=log_summary.next_step,
                gemini_job=gemini_job,
                decision_trace=decision_trace,
            )
    elif request.input_kind == "diff":
        diff_summary = summarize_diff(DiffSummaryRequest(repo=request.repo or "MiddayCommander", diff_text=request.context))
        decision_trace = diff_summary.decision_trace
        if diff_summary.recommended_tool == "human":
            response = DispatchTaskResponse(
                run_id=run_id,
                route="human",
                task_type="review",
                severity=diff_summary.risk_level,
                problem_summary=diff_summary.summary,
                next_step=diff_summary.next_step,
                human_summary="\n".join(diff_summary.review_focus),
                block_reason="High-risk diff requires human review.",
                decision_trace=decision_trace,
            )
        elif diff_summary.recommended_tool == "codex":
            likely_files = profile.common_likely_files if profile else []
            brief = build_codex_brief(
                CodexBriefRequest(
                    title=request.title,
                    repo=request.repo or "MiddayCommander",
                    context="{0}\n\nReview focus:\n- {1}".format(
                        diff_summary.summary,
                        "\n- ".join(diff_summary.review_focus),
                    ),
                    constraints=request.constraints,
                    notes=[diff_summary.next_step],
                    task_type="review",
                    likely_files=likely_files,
                )
            )
            brief_path = _artifact_path(settings.storage_dir, "reports", run_id, "codex-brief", ".md")
            write_text(brief_path, brief.brief_markdown)
            generated_artifacts.append(("codex_brief", brief_path))
            primary_artifact_path = str(brief_path)
            response = DispatchTaskResponse(
                run_id=run_id,
                route="codex",
                task_type="review",
                severity=diff_summary.risk_level,
                problem_summary=diff_summary.summary,
                next_step=diff_summary.next_step,
                codex_brief_markdown=brief.brief_markdown,
                decision_trace=decision_trace,
            )
        else:
            classification = classify_task(
                TaskClassificationRequest(
                    title=request.title,
                    context=request.context,
                    repo=request.repo,
                    source=request.source,
                    constraints=request.constraints,
                )
            )
            gemini_job = build_gemini_job(settings, request, classification, run_id=run_id, profile=profile)
            gemini_job_path = _artifact_path(settings.storage_dir, "gemini_runs", run_id, "job", ".json")
            write_json(gemini_job_path, gemini_job.model_dump())
            generated_artifacts.append(("gemini_job", gemini_job_path))
            primary_artifact_path = str(gemini_job_path)
            response = DispatchTaskResponse(
                run_id=run_id,
                route="gemini",
                task_type="review",
                severity=diff_summary.risk_level,
                problem_summary=diff_summary.summary,
                next_step=diff_summary.next_step,
                gemini_job=gemini_job,
                decision_trace=decision_trace,
            )
    elif request.input_kind == "report":
        report = build_daily_report(DailyReportRequest(repo=request.repo, raw_text=request.context))
        report_path = _artifact_path(settings.storage_dir, "reports", run_id, "daily-report", ".md")
        write_text(report_path, report.markdown)
        generated_artifacts.append(("daily_report", report_path))
        primary_artifact_path = str(report_path)
        response = DispatchTaskResponse(
            run_id=run_id,
            route="local",
            task_type="research",
            severity="low",
            problem_summary="Prepared daily report content.",
            next_step="Review the local report and share it with the team.",
            local_summary=report.markdown,
        )
    else:
        classification = classify_task(
            TaskClassificationRequest(
                title=request.title,
                context=request.context,
                repo=request.repo,
                source=request.source,
                constraints=request.constraints,
            )
        )
        decision_trace = classification.decision_trace
        if classification.recommended_tool == "codex":
            likely_files = profile.common_likely_files if profile else []
            brief = build_codex_brief(
                CodexBriefRequest(
                    title=request.title,
                    repo=request.repo or "MiddayCommander",
                    context=request.context,
                    constraints=request.constraints,
                    notes=[classification.next_step],
                    likely_files=likely_files,
                )
            )
            brief_path = _artifact_path(settings.storage_dir, "reports", run_id, "codex-brief", ".md")
            write_text(brief_path, brief.brief_markdown)
            generated_artifacts.append(("codex_brief", brief_path))
            primary_artifact_path = str(brief_path)
            response = DispatchTaskResponse(
                run_id=run_id,
                route="codex",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                codex_brief_markdown=brief.brief_markdown,
                decision_trace=decision_trace,
            )
        elif classification.recommended_tool == "gemini":
            gemini_job = build_gemini_job(settings, request, classification, run_id=run_id, profile=profile)
            gemini_job_path = _artifact_path(settings.storage_dir, "gemini_runs", run_id, "job", ".json")
            write_json(gemini_job_path, gemini_job.model_dump())
            generated_artifacts.append(("gemini_job", gemini_job_path))
            primary_artifact_path = str(gemini_job_path)
            response = DispatchTaskResponse(
                run_id=run_id,
                route="gemini",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                gemini_job=gemini_job,
                decision_trace=decision_trace,
            )
        elif classification.recommended_tool == "human":
            response = DispatchTaskResponse(
                run_id=run_id,
                route="human",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                human_summary=classification.problem_summary,
                block_reason="Task contains risky production/security/destructive signals.",
                decision_trace=decision_trace,
            )
        else:
            response = DispatchTaskResponse(
                run_id=run_id,
                route="local",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                local_summary=classification.problem_summary,
                decision_trace=decision_trace,
            )

    generated_metadata = _artifact_metadata(run_id, generated_artifacts)
    response_snapshot_path = _artifact_path(settings.storage_dir, "responses", run_id, "dispatch-response", ".json")
    response.artifacts = DispatchArtifactsBlock(
        request_snapshot_path=str(request_snapshot_path),
        response_snapshot_path=str(response_snapshot_path),
        generated=generated_metadata,
    )
    _persist_response_snapshot(settings, run_id, response)
    artifact_metadata = _artifact_metadata(
        run_id,
        [
            ("request_snapshot", request_snapshot_path),
            *generated_artifacts,
            ("response_snapshot", response_snapshot_path),
        ],
    )

    route_status = {
        "codex": "completed",
        "local": "completed",
        "human": "blocked",
        "gemini": "awaiting_execution",
    }[response.route]
    repository.create_run(
        {
            "run_id": run_id,
            "job_id": response.gemini_job.job_id if response.gemini_job else None,
            "created_at": created_at,
            "finished_at": None,
            "status": "created",
            "route": response.route,
            "input_kind": request.input_kind,
            "repo": request.repo,
            "profile_name": profile_name,
            "title": request.title,
            "task_type": response.task_type,
            "severity": response.severity,
            "problem_summary": response.problem_summary,
            "next_step": response.next_step,
            "blocked_flag": 0,
            "timeout_flag": 0,
            "interrupted_flag": 0,
            "needs_human_flag": 0,
            "block_reason": response.block_reason,
            "artifact_dir": str(settings.storage_dir),
            "request_snapshot_path": str(request_snapshot_path),
            "response_snapshot_path": str(response_snapshot_path),
            "final_artifact_path": primary_artifact_path,
            "timing_total_ms": 0,
            "timing_model_ms": 0,
            "timing_exec_ms": 0,
            "command_count": 0,
            "actor": "router",
            "source": request.source,
            "schema_version": "1",
        }
    )
    repository.replace_run_rules(run_id, [rule.model_dump() for rule in response.decision_trace.matched_rules])
    repository.upsert_artifacts([{"run_id": run_id, **item.model_dump()} for item in artifact_metadata])
    repository.update_run(
        run_id,
        {
            "status": route_status,
            "finished_at": None if route_status == "awaiting_execution" else iso_now(),
            "blocked_flag": 1 if response.route == "human" else 0,
            "needs_human_flag": 1 if response.route == "human" else 0,
            "block_reason": response.block_reason,
            "final_artifact_path": primary_artifact_path,
        },
    )
    return response
