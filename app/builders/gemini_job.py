from __future__ import annotations

import json
import uuid

from app.core.settings import Settings
from app.schemas.compress import CompressContextRequest
from app.schemas.dispatch import DispatchTaskRequest
from app.schemas.gemini_job import GeminiJob, GeminiJobOutputContract
from app.schemas.profile import ProfileDefinition
from app.schemas.task import TaskClassificationResponse
from app.services.command_catalog import allowed_command_ids
from app.builders.prompt_compressor import compress_context
from app.utils.prompts import load_prompt, render_prompt


def build_gemini_job(
    settings: Settings,
    request: DispatchTaskRequest,
    classification: TaskClassificationResponse,
    *,
    run_id: str = "",
    profile: ProfileDefinition | None = None,
) -> GeminiJob:
    job_id = "gemini-job-{0}".format(uuid.uuid4().hex)
    compressed = compress_context(
        CompressContextRequest(
            title=request.title,
            context=request.context,
            repo=request.repo,
            constraints=request.constraints,
            target_tool="gemini",
        )
    )
    profile_name = profile.repo_name if profile else ""
    prompt_hints = profile.prompt_hints if profile else []
    template = load_prompt(settings.prompts_dir, "build_gemini_job.txt")
    payload = {
        "run_id": run_id,
        "job_id": job_id,
        "title": request.title,
        "repo": request.repo,
        "profile_name": profile_name,
        "problem_summary": classification.problem_summary,
        "context_digest": compressed.compressed_context,
        "constraints": request.constraints,
        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
        "allowed_command_ids": allowed_command_ids(),
        "prompt_hints": prompt_hints,
    }
    prompt = render_prompt(template, job_json=json.dumps(payload, ensure_ascii=False, indent=2))
    return GeminiJob(
        run_id=run_id,
        job_id=job_id,
        title=request.title,
        repo=request.repo,
        profile_name=profile_name,
        problem_summary=classification.problem_summary,
        context_digest=compressed.compressed_context,
        constraints=request.constraints,
        allowed_hosts=["local", "UbuntuDesktop", "UbuntuServer"],
        allowed_command_ids=allowed_command_ids(),
        output_contract=GeminiJobOutputContract(),
        prompt=prompt,
    )
