from __future__ import annotations

import unittest

from app.core.runtime import bootstrap_runtime
from app.services.run_index import get_run_index
from tests.helpers import temporary_settings_env


class RunIndexTestCase(unittest.TestCase):
    def test_bootstrap_runtime_logs_migration_state(self) -> None:
        with temporary_settings_env():
            from app.core.settings import get_settings

            settings = get_settings()
            with self.assertLogs("codex_bridge.runtime", level="INFO") as logs:
                runtime = bootstrap_runtime(settings)
            self.assertGreaterEqual(len(runtime.profile_names), 1)
            log_line = "\n".join(logs.output)
            self.assertIn("db_path=", log_line)
            self.assertIn("current_user_version=", log_line)
            self.assertIn("applied_migrations=", log_line)
            self.assertIn("final_user_version=", log_line)

    def test_run_index_insert_and_query(self) -> None:
        with temporary_settings_env():
            from app.core.settings import get_settings

            settings = get_settings()
            repository = get_run_index(settings)
            repository.create_run(
                {
                    "run_id": "run-test-001",
                    "job_id": "job-test-001",
                    "created_at": "2026-04-09T01:00:00Z",
                    "finished_at": None,
                    "status": "awaiting_execution",
                    "route": "gemini",
                    "input_kind": "task",
                    "repo": "codex-bridge",
                    "profile_name": "codex-bridge",
                    "title": "Inspect service health",
                    "task_type": "ops",
                    "severity": "medium",
                    "problem_summary": "Inspect service health.",
                    "next_step": "Run safe inspection commands.",
                    "blocked_flag": 0,
                    "timeout_flag": 0,
                    "interrupted_flag": 0,
                    "needs_human_flag": 0,
                    "block_reason": "",
                    "artifact_dir": str(settings.storage_dir),
                    "request_snapshot_path": "",
                    "response_snapshot_path": "",
                    "final_artifact_path": "",
                    "timing_total_ms": 0,
                    "timing_model_ms": 0,
                    "timing_exec_ms": 0,
                    "command_count": 0,
                    "actor": "router",
                    "source": "test",
                    "schema_version": "1",
                }
            )
            repository.replace_run_rules(
                "run-test-001",
                [
                    {
                        "rule_name": "ops_keyword",
                        "rule_type": "keyword",
                        "matched_value": "systemctl",
                        "effect": "classify:ops",
                        "note": "",
                    }
                ],
            )
            repository.upsert_run_commands(
                "run-test-001",
                [
                    {
                        "ordinal": 1,
                        "host": "UbuntuDesktop",
                        "command_id": "systemctl_status",
                        "reason": "Inspect service state.",
                        "shell_command": "systemctl status codex-bridge --no-pager",
                        "status": "ok",
                        "exit_code": 0,
                        "started_at": "2026-04-09T01:00:01Z",
                        "finished_at": "2026-04-09T01:00:02Z",
                        "duration_ms": 1000,
                        "truncated_flag": 0,
                        "stdout_excerpt": "active (running)",
                        "stderr_excerpt": "",
                        "output_path": "/tmp/output.txt",
                    }
                ],
            )
            repository.upsert_artifacts(
                [
                    {
                        "run_id": "run-test-001",
                        "artifact_type": "request_snapshot",
                        "path": "/tmp/request.json",
                        "content_type": "application/json",
                        "created_at": "2026-04-09T01:00:00Z",
                        "size_bytes": 42,
                        "sha256": "abc123",
                    }
                ]
            )
            repository.update_run(
                "run-test-001",
                {
                    "status": "completed",
                    "finished_at": "2026-04-09T01:00:03Z",
                    "timing_total_ms": 3000,
                    "timing_model_ms": 1200,
                    "timing_exec_ms": 900,
                    "command_count": 1,
                },
            )

            run = repository.get_run("run-test-001")
            self.assertIsNotNone(run)
            self.assertEqual(run["status"], "completed")
            self.assertEqual(len(repository.get_run_rules("run-test-001")), 1)
            self.assertEqual(len(repository.get_run_commands("run-test-001")), 1)
            self.assertEqual(len(repository.get_artifacts("run-test-001")), 1)
