from __future__ import annotations

import unittest

from app.execution.validator import validate_command_spec
from tests.helpers import temporary_client


class ExecutionValidationTestCase(unittest.TestCase):
    def test_validate_command_spec_forbidden_host(self) -> None:
        errors = validate_command_spec(
            {"host": "ProductionBastion", "command_id": "uptime", "args": {}},
            ["codex-bridge"],
        )
        self.assertIn("host_not_allowed", errors)

    def test_validate_command_spec_unknown_command(self) -> None:
        errors = validate_command_spec(
            {"host": "local", "command_id": "rm_everything", "args": {}},
            ["codex-bridge"],
        )
        self.assertIn("command_id_not_allowed", errors)

    def test_validate_command_spec_journalctl_limit(self) -> None:
        errors = validate_command_spec(
            {
                "host": "UbuntuServer",
                "command_id": "journalctl_service",
                "args": {"service": "codex-bridge", "lines": 500},
            },
            ["codex-bridge"],
        )
        self.assertIn("journalctl_line_limit_exceeded", errors)

    def test_internal_callback_is_idempotent(self) -> None:
        with temporary_client() as (client, _temp_root):
            dispatch = client.post(
                "/v1/dispatch/task",
                json={
                    "title": "Inspect codex-bridge health",
                    "input_kind": "task",
                    "context": "Check systemctl status and router health with safe commands only.",
                    "repo": "codex-bridge",
                    "source": "test",
                    "constraints": ["Safe commands only"],
                },
            )
            self.assertEqual(dispatch.status_code, 200)
            run_id = dispatch.json()["run_id"]
            payload = {
                "phase": "final",
                "status": "ok",
                "summary": "Inspection completed.",
                "confidence": "high",
                "why": "Commands were safe and succeeded.",
                "final_markdown": "### Done",
                "needs_human": False,
                "timeout_flag": False,
                "interrupted_flag": False,
                "block_reason": "",
                "timing": {
                    "finished_at": "2026-04-09T02:00:00Z",
                    "gemini_cli_duration_ms": 1000,
                    "exec_duration_ms": 500,
                    "total_duration_ms": 1600,
                },
                "results": [
                    {
                        "ordinal": 1,
                        "host": "UbuntuDesktop",
                        "command_id": "systemctl_status",
                        "reason": "Inspect service state.",
                        "shell_command": "systemctl status codex-bridge --no-pager",
                        "status": "ok",
                        "exit_code": 0,
                        "started_at": "2026-04-09T01:59:58Z",
                        "finished_at": "2026-04-09T01:59:59Z",
                        "duration_ms": 900,
                        "stdout_excerpt": "active (running)",
                        "stderr_excerpt": "",
                        "truncated_flag": False,
                        "output_path": "/tmp/codex-bridge-status.txt",
                    }
                ],
                "artifacts": [
                    {
                        "artifact_type": "execution_result",
                        "path": "/tmp/codex-bridge-execution.json",
                        "content_type": "application/json",
                        "created_at": "2026-04-09T02:00:00Z",
                        "size_bytes": 120,
                        "sha256": "abc123",
                    }
                ],
            }

            first = client.post(
                f"/v1/internal/runs/{run_id}/execution",
                json=payload,
                headers={"X-Codex-Bridge-Token": "test-internal-token"},
            )
            second = client.post(
                f"/v1/internal/runs/{run_id}/execution",
                json=payload,
                headers={"X-Codex-Bridge-Token": "test-internal-token"},
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)

            detail = client.get(f"/v1/runs/{run_id}")
            self.assertEqual(detail.status_code, 200)
            detail_payload = detail.json()
            self.assertEqual(detail_payload["run"]["status"], "ok")
            self.assertEqual(detail_payload["run"]["command_count"], 1)
            self.assertEqual(len(detail_payload["commands"]), 1)

    def test_internal_callback_rejects_invalid_token(self) -> None:
        with temporary_client() as (client, _temp_root):
            response = client.post(
                "/v1/internal/runs/run-missing/execution",
                json={"phase": "final", "status": "blocked"},
                headers={"X-Codex-Bridge-Token": "wrong-token"},
            )
            self.assertEqual(response.status_code, 401)
