from __future__ import annotations

from pathlib import Path
from typing import Any

from app.execution.adapters.local import run_local_command
from app.execution.adapters.ssh import run_ssh_command
from app.execution.result_normalizer import normalize_execution_result
from app.execution.validator import build_shell_command, validate_command_spec
from app.schemas.execution import ExecutionBatchResult, ExecutionCommand, ExecutionPlan
from app.utils.files import iso_now, write_text


def _capture_stamp_ms() -> tuple[str, int]:
    import time

    return iso_now(), int(time.time() * 1000)


def execute_plan(
    plan: ExecutionPlan,
    *,
    run_id: str,
    runs_dir: Path,
    base_url: str,
    runtime_host: str,
    desktop_host: str,
    allowed_restart_services: list[str],
) -> ExecutionBatchResult:
    if plan.needs_human:
        return ExecutionBatchResult(
            run_id=run_id,
            phase="final",
            status="blocked",
            summary=plan.summary or "Gemini requested human review.",
            confidence=plan.confidence,
            why=plan.why or "Gemini requested human review.",
            final_markdown=plan.final_markdown,
            needs_human=True,
            block_reason=plan.why or "Gemini requested human review.",
            results=[],
        )

    results = []
    for ordinal, raw_command in enumerate(plan.commands, start=1):
        command = raw_command if isinstance(raw_command, ExecutionCommand) else ExecutionCommand.model_validate(raw_command)
        errors = validate_command_spec(command, allowed_restart_services)
        if errors:
            return ExecutionBatchResult(
                run_id=run_id,
                phase="final",
                status="blocked",
                summary=plan.summary or "Execution plan blocked by validator.",
                confidence=plan.confidence,
                why=", ".join(errors),
                final_markdown=plan.final_markdown,
                needs_human=True,
                block_reason=", ".join(errors),
                results=results,
            )

        shell_command = build_shell_command(
            command.command_id,
            command.args,
            base_url=base_url,
            allowed_restart_services=allowed_restart_services,
        )
        if not shell_command:
            return ExecutionBatchResult(
                run_id=run_id,
                phase="final",
                status="blocked",
                summary=plan.summary or "Execution plan blocked by invalid command build.",
                confidence=plan.confidence,
                why=f"command_build_failed:{command.command_id}",
                final_markdown=plan.final_markdown,
                needs_human=True,
                block_reason=f"command_build_failed:{command.command_id}",
                results=results,
            )

        started_at, started_ms = _capture_stamp_ms()
        if command.host == "local":
            completed = run_local_command(shell_command)
        elif command.host == "UbuntuDesktop":
            completed = run_ssh_command(desktop_host, shell_command)
        else:
            completed = run_ssh_command(runtime_host, shell_command)
        finished_at, finished_ms = _capture_stamp_ms()
        output_path = runs_dir / f"{run_id}-command-{ordinal:03d}.txt"
        write_text(output_path, (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or ""))
        results.append(
            normalize_execution_result(
                ordinal=ordinal,
                command=command,
                shell_command=shell_command,
                completed=completed,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=max(0, finished_ms - started_ms),
                output_path=str(output_path),
            )
        )

    status = "ok" if all((item.exit_code or 0) == 0 for item in results) else "failed"
    return ExecutionBatchResult(
        run_id=run_id,
        phase="final",
        status=status,
        summary=plan.summary,
        confidence=plan.confidence,
        why=plan.why,
        final_markdown=plan.final_markdown,
        needs_human=plan.needs_human,
        block_reason=plan.why if status != "ok" else "",
        results=results,
    )
