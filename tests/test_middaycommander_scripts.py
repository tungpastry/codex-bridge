from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiddayCommanderScriptTestCase(unittest.TestCase):
    def run_script(self, script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
        temp_root = Path(tempfile.mkdtemp(prefix="midday-bridge-test-"))
        reports_dir = temp_root / "storage" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(
            {
                "MIDDAY_TARGET_DEFAULTS_FILE": "/dev/null",
                "MIDDAY_TARGET_ENV_FILE": "/dev/null",
                "CODEX_BRIDGE_ENV_FILE": "/dev/null",
                "MIDDAY_MAC_ROOT": "/tmp/MiddayCommander",
                "MIDDAY_BRIDGE_MAC_ROOT": str(ROOT),
                "MIDDAY_ROUTER_BASE_URL": "http://127.0.0.1:8787",
                "MIDDAY_DESKTOP_SSH": "nexus@192.168.1.15",
                "MIDDAY_SERVER_SSH": "nexus@192.168.1.30",
                "MIDDAY_SERVER_ROOT": "/home/nexus/projects/MiddayCommander",
                "MIDDAY_ROUTER_SERVICE": "codex-bridge.service",
                "MIDDAY_REPORTS_DIR": str(reports_dir),
            }
        )
        return subprocess.run(
            [str(ROOT / "scripts" / "mac" / script_name), *args],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_deploy_router_dry_run(self) -> None:
        result = self.run_script("middaycommander-deploy-router.sh", "--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MiddayCommander Router Deploy (dry run)", result.stdout)
        self.assertIn("/home/nexus/codex-bridge", result.stdout)
        self.assertIn("codex-bridge.service", result.stdout)

    def test_health_dry_run(self) -> None:
        result = self.run_script("middaycommander-health.sh", "--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("## Router", result.stdout)
        self.assertIn("## MiddayCommander Repo", result.stdout)
        self.assertIn("Run without --dry-run", result.stdout)

    def test_morning_check_dry_run(self) -> None:
        result = self.run_script("middaycommander-morning-check.sh", "--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MiddayCommander Morning Check (dry run)", result.stdout)
        self.assertIn("storage/reports", result.stdout)
        self.assertIn("middaycommander-health.sh", result.stdout)


if __name__ == "__main__":
    unittest.main()
