from __future__ import annotations

from subprocess import CompletedProcess

from app.execution.redaction import excerpt_text
from app.schemas.execution import ExecutionCommand, ExecutionResult


def normalize_execution_result(
    *,
    ordinal: int,
    command: ExecutionCommand,
    shell_command: str,
    completed: CompletedProcess[str],
    started_at: str,
    finished_at: str,
    duration_ms: int,
    output_path: str = "",
) -> ExecutionResult:
    stdout_excerpt, stdout_truncated = excerpt_text(completed.stdout)
    stderr_excerpt, stderr_truncated = excerpt_text(completed.stderr)
    return ExecutionResult(
        ordinal=ordinal,
        host=command.host,
        command_id=command.command_id,
        reason=command.reason,
        shell_command=shell_command,
        status="ok" if completed.returncode == 0 else "failed",
        exit_code=completed.returncode,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        stdout_excerpt=stdout_excerpt,
        stderr_excerpt=stderr_excerpt,
        truncated_flag=stdout_truncated or stderr_truncated,
        output_path=output_path,
    )
