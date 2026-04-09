from __future__ import annotations

import unittest

from app.services.run_index import get_run_index
from tests.helpers import temporary_client


class RunsApiTestCase(unittest.TestCase):
    def test_runs_endpoints_and_metrics(self) -> None:
        with temporary_client() as (client, _temp_root):
            first = client.post(
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
            self.assertEqual(first.status_code, 200)
            first_payload = first.json()

            second = client.post(
                "/v1/dispatch/task",
                json={
                    "title": "Production schema change",
                    "input_kind": "task",
                    "context": "Need schema migration in production and auth change.",
                    "repo": "codex-bridge",
                    "source": "test",
                    "constraints": [],
                },
            )
            self.assertEqual(second.status_code, 200)
            second_payload = second.json()

            runs_response = client.get("/v1/runs", params={"repo": "codex-bridge"})
            self.assertEqual(runs_response.status_code, 200)
            runs_payload = runs_response.json()
            self.assertGreaterEqual(runs_payload["total"], 2)
            self.assertGreaterEqual(len(runs_payload["items"]), 2)

            run_detail = client.get(f"/v1/runs/{first_payload['run_id']}")
            self.assertEqual(run_detail.status_code, 200)
            detail_payload = run_detail.json()
            self.assertEqual(detail_payload["run"]["run_id"], first_payload["run_id"])
            self.assertGreaterEqual(len(detail_payload["artifacts"]), 2)

            artifacts_response = client.get(f"/v1/runs/{first_payload['run_id']}/artifacts")
            self.assertEqual(artifacts_response.status_code, 200)
            self.assertEqual(artifacts_response.json()["run_id"], first_payload["run_id"])

            blocked_runs = client.get("/v1/runs", params={"status": "blocked"})
            self.assertEqual(blocked_runs.status_code, 200)
            self.assertTrue(any(item["run_id"] == second_payload["run_id"] for item in blocked_runs.json()["items"]))

            metrics_response = client.get("/v1/admin/metrics")
            self.assertEqual(metrics_response.status_code, 200)
            metrics_payload = metrics_response.json()
            self.assertGreaterEqual(metrics_payload["runs_total"], 2)
            self.assertGreaterEqual(metrics_payload["blocked_today"], 1)

            health_response = client.get("/health", params={"depth": "full"})
            self.assertEqual(health_response.status_code, 200)
            health_payload = health_response.json()
            self.assertEqual(health_payload["depth"], "full")
            self.assertEqual(health_payload["index"]["status"], "ok")
            self.assertGreaterEqual(health_payload["profiles"]["count"], 1)

    def test_runs_list_uses_created_at_desc_by_default(self) -> None:
        with temporary_client() as (client, _temp_root):
            from app.core.settings import get_settings

            repository = get_run_index(get_settings())
            base_payload = {
                "job_id": None,
                "finished_at": None,
                "status": "completed",
                "route": "local",
                "input_kind": "report",
                "repo": "codex-bridge",
                "profile_name": "codex-bridge",
                "task_type": "research",
                "severity": "low",
                "problem_summary": "Prepared report.",
                "next_step": "Share it.",
                "blocked_flag": 0,
                "timeout_flag": 0,
                "interrupted_flag": 0,
                "needs_human_flag": 0,
                "block_reason": "",
                "artifact_dir": "",
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
            repository.create_run(
                {
                    **base_payload,
                    "run_id": "run-sort-old",
                    "created_at": "2026-04-09T01:00:00Z",
                    "title": "Old run",
                }
            )
            repository.create_run(
                {
                    **base_payload,
                    "run_id": "run-sort-new",
                    "created_at": "2026-04-09T02:00:00Z",
                    "title": "New run",
                }
            )

            response = client.get("/v1/runs", params={"repo": "codex-bridge", "limit": 2})
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["items"][0]["run_id"], "run-sort-new")
            self.assertEqual(payload["items"][1]["run_id"], "run-sort-old")
