from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PROMPTS_DIR", str(ROOT / "prompts"))
os.environ.setdefault("STORAGE_DIR", str(ROOT / "storage"))

from fastapi.testclient import TestClient

from app.main import app
from app.services.command_catalog import validate_command_spec


class RouterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["service"], "codex-bridge")
        self.assertEqual(payload["status"], "ok")

    def test_classify_bugfix_vietnamese(self) -> None:
        response = self.client.post(
            "/v1/classify/task",
            json={
                "title": "MiddayCommander loi build",
                "context": "Go test that bai voi panic trong transfer queue.",
                "repo": "MiddayCommander",
                "source": "test",
                "constraints": ["Patch nho"],
            },
        )
        payload = response.json()
        self.assertEqual(payload["task_type"], "bugfix")
        self.assertEqual(payload["recommended_tool"], "codex")

    def test_classify_ops_english(self) -> None:
        response = self.client.post(
            "/v1/classify/task",
            json={
                "title": "Check production service",
                "context": "Use journalctl and systemctl to inspect the deploy issue.",
                "repo": "codex-bridge",
                "source": "test",
                "constraints": [],
            },
        )
        payload = response.json()
        self.assertIn(payload["task_type"], ("deploy", "ops"))
        self.assertEqual(payload["recommended_tool"], "gemini")

    def test_dispatch_human_for_risky_task(self) -> None:
        response = self.client.post(
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
        payload = response.json()
        self.assertEqual(payload["route"], "human")
        self.assertTrue(payload["block_reason"])

    def test_dispatch_diff_for_middaycommander(self) -> None:
        response = self.client.post(
            "/v1/dispatch/task",
            json={
                "title": "Review MiddayCommander patch",
                "input_kind": "diff",
                "context": "diff --git a/internal/fs/router.go b/internal/fs/router.go\n+++ b/internal/fs/router.go\n@@\n+if err != nil { return err }\n",
                "repo": "MiddayCommander",
                "source": "test",
                "constraints": [],
            },
        )
        payload = response.json()
        self.assertIn(payload["route"], ("codex", "gemini"))

    def test_dispatch_gemini_job_has_job_id(self) -> None:
        response = self.client.post(
            "/v1/dispatch/task",
            json={
                "title": "Inspect codex-bridge health",
                "input_kind": "task",
                "context": "Check service status and router health only with safe commands",
                "repo": "codex-bridge",
                "source": "test",
                "constraints": ["Safe commands only"],
            },
        )
        payload = response.json()
        if payload["route"] != "gemini":
            self.skipTest("dispatch route did not resolve to gemini in this environment")
        self.assertTrue(payload["gemini_job"]["job_id"])

    def test_dispatch_codex_bridge_gemini_job_prefers_desktop_hosts(self) -> None:
        response = self.client.post(
            "/v1/dispatch/task",
            json={
                "title": "Inspect codex-bridge health",
                "input_kind": "task",
                "context": "Use systemctl and journalctl to inspect the codex-bridge service safely.",
                "repo": "codex-bridge",
                "source": "test",
                "constraints": ["Safe commands only"],
            },
        )
        payload = response.json()
        if payload["route"] != "gemini":
            self.skipTest("dispatch route did not resolve to gemini in this environment")
        job = payload["gemini_job"]
        self.assertEqual(job["preferred_command_hosts"]["journalctl_service"], "UbuntuDesktop")
        self.assertEqual(job["preferred_command_hosts"]["systemctl_status"], "UbuntuDesktop")
        self.assertIn("preferred_command_hosts", job["prompt"])
        self.assertIn("UbuntuDesktop", job["prompt"])

    def test_report_daily_bilingual(self) -> None:
        response = self.client.post(
            "/v1/report/daily",
            json={
                "items": [
                    "Done: added dispatch route",
                    "Open: service restart policy still needs review",
                    "Tiep theo: verify Gemini runner on Mac mini",
                ]
            },
        )
        payload = response.json()
        self.assertIn("## Done", payload["markdown"])
        self.assertIn("## Open Issues", payload["markdown"])
        self.assertIn("## Next Actions", payload["markdown"])

    def test_validate_command_spec_rejects_restart(self) -> None:
        errors = validate_command_spec(
            {
                "host": "UbuntuServer",
                "command_id": "service_restart",
                "args": {"service": "unknown-service"},
            },
            ["codex-bridge", "postgresql"],
        )
        self.assertIn("service_restart_not_allowed", errors)

    def test_validate_command_spec_accepts_journalctl(self) -> None:
        errors = validate_command_spec(
            {
                "host": "UbuntuServer",
                "command_id": "journalctl_service",
                "args": {"service": "codex-bridge", "lines": 200},
            },
            ["codex-bridge", "postgresql"],
        )
        self.assertEqual(errors, [])

    @unittest.skipUnless(shutil.which("jq"), "jq is required for runner shell tests")
    def test_runner_outputs_timing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            job_id = "test-gemini-job-ok"
            job_file = temp_root / "job.json"
            mock_file = temp_root / "mock-response.json"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": "ops_auto",
                        "title": "Inspect local uptime",
                        "repo": "codex-bridge",
                        "problem_summary": "Inspect local uptime",
                        "context_digest": "Use a safe local uptime command.",
                        "constraints": ["Safe commands only"],
                        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
                        "allowed_command_ids": ["uptime"],
                        "output_contract": {
                            "summary": "Short human-readable summary",
                            "confidence": "low|medium|high",
                            "needs_human": "true|false",
                            "why": "Why the plan is safe or why it needs escalation",
                            "commands": "Array of {host, command_id, args, reason}",
                            "final_markdown": "Operator-ready markdown summary",
                        },
                        "prompt": "Return JSON only.",
                    }
                ),
                encoding="utf-8",
            )
            mock_file.write_text(
                json.dumps(
                    {
                        "response": json.dumps(
                            {
                                "summary": "Inspecting local uptime.",
                                "confidence": "high",
                                "needs_human": False,
                                "why": "This uses a safe local read-only command.",
                                "commands": [
                                    {
                                        "host": "local",
                                        "command_id": "uptime",
                                        "args": {},
                                        "reason": "Check local uptime.",
                                    }
                                ],
                                "final_markdown": "### Mock Plan",
                            }
                        )
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["CODEX_BRIDGE_MAC_ROOT"] = str(temp_root)
            env["CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE"] = str(mock_file)
            result = subprocess.run(
                [str(ROOT / "scripts/mac/codex-bridge-run-gemini.sh"), "--job-file", str(job_file)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["run_id"], job_id)
            self.assertEqual(payload["job_id"], job_id)
            self.assertIn("timing", payload)
            self.assertIn("timing_summary", payload)
            self.assertGreaterEqual(payload["timing"]["gemini_cli_duration_ms"], 0)
            self.assertGreaterEqual(
                payload["timing"]["total_duration_ms"],
                payload["timing"]["gemini_cli_duration_ms"],
            )
            self.assertIn("## Timing", payload["final_markdown"])

            runs_dir = temp_root / "storage" / "gemini_runs"
            for suffix in ("job", "gemini-output", "plan", "exec-results", "timing", "final"):
                self.assertTrue((runs_dir / f"{job_id}-{suffix}.json").exists())

    @unittest.skipUnless(shutil.which("jq"), "jq is required for runner shell tests")
    def test_runner_extracts_json_after_banner_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            job_id = "test-gemini-job-banner"
            job_file = temp_root / "job.json"
            mock_file = temp_root / "mock-response.txt"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": "ops_auto",
                        "title": "Inspect local uptime after banner output",
                        "repo": "codex-bridge",
                        "problem_summary": "Inspect local uptime after banner output",
                        "context_digest": "Use a safe local uptime command.",
                        "constraints": ["Safe commands only"],
                        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
                        "allowed_command_ids": ["uptime"],
                        "output_contract": {
                            "summary": "Short human-readable summary",
                            "confidence": "low|medium|high",
                            "needs_human": "true|false",
                            "why": "Why the plan is safe or why it needs escalation",
                            "commands": "Array of {host, command_id, args, reason}",
                            "final_markdown": "Operator-ready markdown summary",
                        },
                        "prompt": "Return JSON only.",
                    }
                ),
                encoding="utf-8",
            )
            mock_file.write_text(
                'Loaded cached credentials.\n'
                'Loaded cached credentials.\n'
                + json.dumps(
                    {
                        "response": json.dumps(
                            {
                                "summary": "Inspecting local uptime.",
                                "confidence": "high",
                                "needs_human": False,
                                "why": "This uses a safe local read-only command.",
                                "commands": [
                                    {
                                        "host": "local",
                                        "command_id": "uptime",
                                        "args": {},
                                        "reason": "Check local uptime.",
                                    }
                                ],
                                "final_markdown": "### Mock Plan",
                            }
                        )
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["CODEX_BRIDGE_MAC_ROOT"] = str(temp_root)
            env["CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE"] = str(mock_file)
            result = subprocess.run(
                [str(ROOT / "scripts/mac/codex-bridge-run-gemini.sh"), "--job-file", str(job_file)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["run_id"], job_id)

            runs_dir = temp_root / "storage" / "gemini_runs"
            gemini_output = json.loads((runs_dir / f"{job_id}-gemini-output.json").read_text(encoding="utf-8"))
            self.assertIn("response", gemini_output)

    @unittest.skipUnless(shutil.which("jq"), "jq is required for runner shell tests")
    def test_runner_blocked_plan_keeps_timing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            job_id = "test-gemini-job-blocked"
            job_file = temp_root / "job.json"
            mock_file = temp_root / "mock-response.json"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": "ops_auto",
                        "title": "Blocked plan",
                        "repo": "codex-bridge",
                        "problem_summary": "This plan should escalate to a human.",
                        "context_digest": "Human escalation test.",
                        "constraints": ["Safe commands only"],
                        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
                        "allowed_command_ids": ["uptime"],
                        "output_contract": {
                            "summary": "Short human-readable summary",
                            "confidence": "low|medium|high",
                            "needs_human": "true|false",
                            "why": "Why the plan is safe or why it needs escalation",
                            "commands": "Array of {host, command_id, args, reason}",
                            "final_markdown": "Operator-ready markdown summary",
                        },
                        "prompt": "Return JSON only.",
                    }
                ),
                encoding="utf-8",
            )
            mock_file.write_text(
                json.dumps(
                    {
                        "response": json.dumps(
                            {
                                "summary": "Needs human review.",
                                "confidence": "low",
                                "needs_human": True,
                                "why": "Manual review required.",
                                "commands": [],
                                "final_markdown": "### Blocked Plan",
                            }
                        )
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["CODEX_BRIDGE_MAC_ROOT"] = str(temp_root)
            env["CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE"] = str(mock_file)
            result = subprocess.run(
                [str(ROOT / "scripts/mac/codex-bridge-run-gemini.sh"), "--job-file", str(job_file)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], job_id)
            self.assertEqual(payload["job_id"], job_id)
            self.assertIn("timing", payload)
            self.assertGreaterEqual(payload["timing"]["total_duration_ms"], 0)
            self.assertIn("## Timing", payload["final_markdown"])

            runs_dir = temp_root / "storage" / "gemini_runs"
            self.assertTrue((runs_dir / f"{job_id}-timing.json").exists())
            self.assertTrue((runs_dir / f"{job_id}-final.json").exists())

    @unittest.skipUnless(shutil.which("jq"), "jq is required for runner shell tests")
    def test_runner_timeout_keeps_partial_timing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            job_id = "test-gemini-job-timeout"
            job_file = temp_root / "job.json"
            fake_gemini = temp_root / "fake-gemini.sh"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": "ops_auto",
                        "title": "Timeout plan",
                        "repo": "codex-bridge",
                        "problem_summary": "This plan should time out.",
                        "context_digest": "Timeout test.",
                        "constraints": ["Safe commands only"],
                        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
                        "allowed_command_ids": ["uptime"],
                        "output_contract": {
                            "summary": "Short human-readable summary",
                            "confidence": "low|medium|high",
                            "needs_human": "true|false",
                            "why": "Why the plan is safe or why it needs escalation",
                            "commands": "Array of {host, command_id, args, reason}",
                            "final_markdown": "Operator-ready markdown summary",
                        },
                        "prompt": "Return JSON only.",
                    }
                ),
                encoding="utf-8",
            )
            fake_gemini.write_text(
                "#!/bin/bash\nsleep 5\nprintf '%s' '{\"response\":\"{}\"}'\n",
                encoding="utf-8",
            )
            fake_gemini.chmod(0o755)

            env = os.environ.copy()
            env["CODEX_BRIDGE_MAC_ROOT"] = str(temp_root)
            env["CODEX_BRIDGE_GEMINI_BIN"] = str(fake_gemini)
            env["CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS"] = "1"
            result = subprocess.run(
                [str(ROOT / "scripts/mac/codex-bridge-run-gemini.sh"), "--job-file", str(job_file)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], job_id)
            self.assertEqual(payload["job_id"], job_id)
            self.assertIn("timed out", payload["why"])
            self.assertIn("timing", payload)
            self.assertGreaterEqual(payload["timing"]["gemini_cli_duration_ms"], 0)
            self.assertGreaterEqual(payload["timing"]["total_duration_ms"], payload["timing"]["gemini_cli_duration_ms"])
            self.assertIn("## Timing", payload["final_markdown"])

            runs_dir = temp_root / "storage" / "gemini_runs"
            self.assertTrue((runs_dir / f"{job_id}-timing.json").exists())
            self.assertTrue((runs_dir / f"{job_id}-final.json").exists())

    @unittest.skipUnless(shutil.which("jq"), "jq is required for runner shell tests")
    def test_runner_auth_prompt_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            job_id = "test-gemini-job-auth"
            job_file = temp_root / "job.json"
            fake_gemini = temp_root / "fake-gemini.sh"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": "ops_auto",
                        "title": "Auth prompt plan",
                        "repo": "codex-bridge",
                        "problem_summary": "This plan should stop on browser auth prompt.",
                        "context_digest": "Auth prompt test.",
                        "constraints": ["Safe commands only"],
                        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
                        "allowed_command_ids": ["uptime"],
                        "output_contract": {
                            "summary": "Short human-readable summary",
                            "confidence": "low|medium|high",
                            "needs_human": "true|false",
                            "why": "Why the plan is safe or why it needs escalation",
                            "commands": "Array of {host, command_id, args, reason}",
                            "final_markdown": "Operator-ready markdown summary",
                        },
                        "prompt": "Return JSON only.",
                    }
                ),
                encoding="utf-8",
            )
            fake_gemini.write_text(
                "#!/usr/bin/env python3\n"
                "import sys, time\n"
                "print('Opening authentication page in your browser. Do you want to continue? [Y/n]:', flush=True)\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            fake_gemini.chmod(0o755)

            env = os.environ.copy()
            env["CODEX_BRIDGE_MAC_ROOT"] = str(temp_root)
            env["CODEX_BRIDGE_GEMINI_BIN"] = str(fake_gemini)
            env["CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS"] = "180"

            started = time.time()
            result = subprocess.run(
                [str(ROOT / "scripts/mac/codex-bridge-run-gemini.sh"), "--job-file", str(job_file)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            elapsed = time.time() - started

            self.assertNotEqual(result.returncode, 0, msg=result.stderr)
            self.assertLess(elapsed, 10.0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], job_id)
            self.assertEqual(payload["job_id"], job_id)
            self.assertIn("interactive browser authentication", payload["why"])
            self.assertTrue(payload["needs_human"])
            self.assertGreaterEqual(payload["timing"]["gemini_cli_duration_ms"], 0)

            runs_dir = temp_root / "storage" / "gemini_runs"
            self.assertTrue((runs_dir / f"{job_id}-timing.json").exists())
            self.assertTrue((runs_dir / f"{job_id}-final.json").exists())

    @unittest.skipUnless(shutil.which("jq"), "jq is required for runner shell tests")
    def test_runner_term_keeps_partial_timing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            job_id = "test-gemini-job-term"
            job_file = temp_root / "job.json"
            fake_gemini = temp_root / "fake-gemini.sh"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "mode": "ops_auto",
                        "title": "Interrupt plan",
                        "repo": "codex-bridge",
                        "problem_summary": "This plan should be interrupted.",
                        "context_digest": "TERM test.",
                        "constraints": ["Safe commands only"],
                        "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
                        "allowed_command_ids": ["uptime"],
                        "output_contract": {
                            "summary": "Short human-readable summary",
                            "confidence": "low|medium|high",
                            "needs_human": "true|false",
                            "why": "Why the plan is safe or why it needs escalation",
                            "commands": "Array of {host, command_id, args, reason}",
                            "final_markdown": "Operator-ready markdown summary",
                        },
                        "prompt": "Return JSON only.",
                    }
                ),
                encoding="utf-8",
            )
            fake_gemini.write_text(
                "#!/bin/bash\nsleep 30\nprintf '%s' '{\"response\":\"{}\"}'\n",
                encoding="utf-8",
            )
            fake_gemini.chmod(0o755)

            env = os.environ.copy()
            env["CODEX_BRIDGE_MAC_ROOT"] = str(temp_root)
            env["CODEX_BRIDGE_GEMINI_BIN"] = str(fake_gemini)
            env["CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS"] = "0"
            proc = subprocess.Popen(
                [str(ROOT / "scripts/mac/codex-bridge-run-gemini.sh"), "--job-file", str(job_file)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.5)
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=10)

            self.assertNotEqual(proc.returncode, 0, msg=stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], job_id)
            self.assertEqual(payload["job_id"], job_id)
            self.assertIn("interrupted by TERM", payload["why"])
            self.assertIn("timing", payload)
            self.assertGreaterEqual(payload["timing"]["total_duration_ms"], 0)
            self.assertIn("## Timing", payload["final_markdown"])

            runs_dir = temp_root / "storage" / "gemini_runs"
            self.assertTrue((runs_dir / f"{job_id}-timing.json").exists())
            self.assertTrue((runs_dir / f"{job_id}-final.json").exists())


if __name__ == "__main__":
    unittest.main()
