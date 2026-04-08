from __future__ import annotations

import json
import uuid

from app.config import Settings
from app.schemas.dispatch import DispatchTaskRequest
from app.schemas.gemini_job import GeminiJob, GeminiJobOutputContract
from app.schemas.task import TaskClassificationResponse
from app.services.command_catalog import allowed_command_ids
from app.services.prompt_compressor import compress_context
from app.schemas.compress import CompressContextRequest
from app.utils.prompts import load_prompt, render_prompt


def build_gemini_job(
    settings: Settings,
    request: DispatchTaskRequest,
    classification: TaskClassificationResponse,
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
    template = load_prompt(settings.prompts_dir, "build_gemini_job.txt")
    payload = {
        "job_id": job_id,
        "title": request.title,
        "repo": request.repo,
        "problem_summary": classification.problem_summary,
        "context_digest": compressed.compressed_context,
        "constraints": request.constraints,
        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
        "allowed_command_ids": allowed_command_ids(),
    }
    prompt = render_prompt(template, job_json=json.dumps(payload, ensure_ascii=False, indent=2))
    return GeminiJob(
        job_id=job_id,
        title=request.title,
        repo=request.repo,
        problem_summary=classification.problem_summary,
        context_digest=compressed.compressed_context,
        constraints=request.constraints,
        allowed_hosts=["local", "UbuntuDesktop", "UbuntuServer"],
        allowed_command_ids=allowed_command_ids(),
        output_contract=GeminiJobOutputContract(),
        prompt=prompt,
    )
