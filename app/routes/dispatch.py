from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.codex_brief import CodexBriefRequest
from app.schemas.diff_summary import DiffSummaryRequest
from app.schemas.dispatch import DispatchTaskRequest, DispatchTaskResponse
from app.schemas.log_summary import LogSummaryRequest
from app.schemas.report import DailyReportRequest
from app.schemas.task import TaskClassificationRequest
from app.services.codex_brief_builder import build_codex_brief
from app.services.diff_summarizer import summarize_diff
from app.services.gemini_dispatcher import build_gemini_job
from app.services.log_triage import summarize_log
from app.services.report_builder import build_daily_report
from app.services.task_router import classify_task
from app.utils.files import save_json_snapshot

router = APIRouter(prefix="/v1/dispatch", tags=["dispatch"])


@router.post("/task", response_model=DispatchTaskResponse)
async def dispatch_task_route(request: DispatchTaskRequest) -> DispatchTaskResponse:
    settings = get_settings()
    save_json_snapshot(settings.storage_dir, "requests", "dispatch-task", request.model_dump())

    if request.input_kind == "log":
        log_summary = summarize_log(
            LogSummaryRequest(
                service=request.target_host,
                log_text=request.context,
                repo=request.repo,
                source=request.source,
            )
        )
        if log_summary.recommended_tool == "codex":
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
                )
            )
            response = DispatchTaskResponse(
                route="codex",
                task_type="bugfix",
                severity="high",
                problem_summary=log_summary.symptom,
                next_step=log_summary.next_step,
                codex_brief_markdown=brief.brief_markdown,
            )
        elif log_summary.recommended_tool == "human":
            response = DispatchTaskResponse(
                route="human",
                task_type="ops",
                severity="critical",
                problem_summary=log_summary.symptom,
                next_step=log_summary.next_step,
                human_summary=log_summary.likely_cause,
                block_reason="Risky log pattern requires human review.",
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
            response = DispatchTaskResponse(
                route="gemini",
                task_type="ops",
                severity="high" if log_summary.recommended_tool == "gemini" else "medium",
                problem_summary=log_summary.symptom,
                next_step=log_summary.next_step,
                gemini_job=build_gemini_job(settings, request, classification),
            )
    elif request.input_kind == "diff":
        diff_summary = summarize_diff(
            DiffSummaryRequest(repo=request.repo or "MiddayCommander", diff_text=request.context)
        )
        if diff_summary.recommended_tool == "human":
            response = DispatchTaskResponse(
                route="human",
                task_type="review",
                severity=diff_summary.risk_level,
                problem_summary=diff_summary.summary,
                next_step=diff_summary.next_step,
                human_summary="\n".join(diff_summary.review_focus),
                block_reason="High-risk diff requires human review.",
            )
        elif diff_summary.recommended_tool == "codex":
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
                )
            )
            response = DispatchTaskResponse(
                route="codex",
                task_type="review",
                severity=diff_summary.risk_level,
                problem_summary=diff_summary.summary,
                next_step=diff_summary.next_step,
                codex_brief_markdown=brief.brief_markdown,
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
            response = DispatchTaskResponse(
                route="gemini",
                task_type="review",
                severity=diff_summary.risk_level,
                problem_summary=diff_summary.summary,
                next_step=diff_summary.next_step,
                gemini_job=build_gemini_job(settings, request, classification),
            )
    elif request.input_kind == "report":
        report = build_daily_report(DailyReportRequest(repo=request.repo, raw_text=request.context))
        response = DispatchTaskResponse(
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
        if classification.recommended_tool == "codex":
            brief = build_codex_brief(
                CodexBriefRequest(
                    title=request.title,
                    repo=request.repo or "MiddayCommander",
                    context=request.context,
                    constraints=request.constraints,
                    notes=[classification.next_step],
                )
            )
            response = DispatchTaskResponse(
                route="codex",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                codex_brief_markdown=brief.brief_markdown,
            )
        elif classification.recommended_tool == "gemini":
            response = DispatchTaskResponse(
                route="gemini",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                gemini_job=build_gemini_job(settings, request, classification),
            )
        elif classification.recommended_tool == "human":
            response = DispatchTaskResponse(
                route="human",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                human_summary=classification.problem_summary,
                block_reason="Task contains risky production/security/destructive signals.",
            )
        else:
            response = DispatchTaskResponse(
                route="local",
                task_type=classification.task_type,
                severity=classification.severity,
                problem_summary=classification.problem_summary,
                next_step=classification.next_step,
                local_summary=classification.problem_summary,
            )

    save_json_snapshot(settings.storage_dir, "responses", "dispatch-task", response.model_dump())
    return response
