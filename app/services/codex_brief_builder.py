from __future__ import annotations

from app.schemas.codex_brief import CodexBriefRequest, CodexBriefResponse
from app.services.task_router import classify_task
from app.schemas.task import TaskClassificationRequest
from app.utils.text import summarize_block, unique_list


def build_codex_brief(request: CodexBriefRequest) -> CodexBriefResponse:
    classification = classify_task(
        TaskClassificationRequest(
            title=request.title,
            context=request.context,
            repo=request.repo,
            source="brief",
            constraints=request.constraints,
        )
    )
    task_type = request.task_type or classification.task_type
    goal = request.goal or summarize_block(request.context, limit=180) or request.title

    sections = [
        "# Codex Brief",
        "",
        "## Task",
        request.title.strip(),
        "",
        "## Repo",
        request.repo.strip(),
        "",
        "## Task Type",
        task_type,
        "",
        "## Goal",
        goal,
        "",
        "## Context",
        request.context.strip(),
        "",
        "## Constraints",
    ]

    constraints = unique_list(request.constraints or ["Keep changes practical and production-friendly."], limit=8)
    sections.extend("- {0}".format(item) for item in constraints)
    sections.extend(["", "## Acceptance Criteria"])
    acceptance = unique_list(
        request.acceptance_criteria
        or [
            "Implement the requested behavior without redesigning the architecture.",
            "Keep the result easy to verify locally.",
        ],
        limit=8,
    )
    sections.extend("- {0}".format(item) for item in acceptance)
    sections.extend(["", "## Likely Files"])
    likely_files = unique_list(request.likely_files or classification.suspected_files or ["Not yet identified"], limit=8)
    sections.extend("- {0}".format(item) for item in likely_files)
    sections.extend(["", "## Notes"])
    notes = unique_list(request.notes or [classification.next_step], limit=8)
    sections.extend("- {0}".format(item) for item in notes)

    return CodexBriefResponse(
        brief_markdown="\n".join(sections).strip() + "\n",
        task_type=task_type,
        recommended_tool="codex",
    )
