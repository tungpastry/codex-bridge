from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiddayCommanderScriptTestCase(unittest.TestCase):
    def run_script(
        self, script_name: str, *args: str, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
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
                "MIDDAY_RELEASE_REPO": "tungpastry/MiddayCommander",
                "MIDDAY_RELEASES_ROOT": "/home/nexus/releases/middaycommander",
                "MIDDAY_RELEASE_BINARY_NAME": "mdc",
                "MIDDAY_RELEASE_SERVER_OS": "linux",
                "MIDDAY_RELEASE_SERVER_ARCH": "amd64",
                "MIDDAY_RELEASE_DIST_DIR": "/tmp/MiddayCommander/dist",
                "MIDDAY_RELEASE_STORAGE_DIR": str(temp_root / "storage" / "releases"),
            }
        )
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(ROOT / "scripts" / "mac" / script_name), *args],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def make_prereq_path(self, *, include_gh: bool, include_goreleaser: bool) -> str:
        temp_bin = Path(tempfile.mkdtemp(prefix="midday-bridge-bin-"))
        required = ["bash", "git", "go", "ssh", "scp", "tar", "jq", "shasum"]
        if include_gh:
            required.append("gh")
        if include_goreleaser:
            required.append("goreleaser")
        for name in required:
            resolved = shutil.which(name)
            if resolved:
                (temp_bin / name).symlink_to(resolved)
            elif name == "gh":
                (temp_bin / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                (temp_bin / name).chmod(0o755)
            elif name == "goreleaser":
                (temp_bin / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                (temp_bin / name).chmod(0o755)
            else:
                self.fail(f"Required command not found on test host: {name}")
        return str(temp_bin)

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
        self.assertIn("## MiddayCommander Release", result.stdout)
        self.assertIn("Run without --dry-run", result.stdout)

    def test_morning_check_dry_run(self) -> None:
        result = self.run_script("middaycommander-morning-check.sh", "--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MiddayCommander Morning Check (dry run)", result.stdout)
        self.assertIn("Release root", result.stdout)
        self.assertIn("storage/reports", result.stdout)
        self.assertIn("middaycommander-health.sh", result.stdout)

    def test_release_dry_run(self) -> None:
        result = self.run_script("middaycommander-release.sh", "--tag", "v9.9.9", "--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MiddayCommander Release (dry run)", result.stdout)
        self.assertIn("tungpastry/MiddayCommander", result.stdout)
        self.assertIn("MiddayCommander_v9.9.9_linux_amd64.tar.gz", result.stdout)

    def test_release_requires_gh(self) -> None:
        test_path = self.make_prereq_path(include_gh=False, include_goreleaser=False)
        result = self.run_script(
            "middaycommander-release.sh",
            "--tag",
            "v9.9.9",
            extra_env={"PATH": f"{test_path}:/usr/bin:/bin:/usr/sbin:/sbin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required command: gh", result.stderr)

    def test_release_requires_goreleaser(self) -> None:
        test_path = self.make_prereq_path(include_gh=True, include_goreleaser=False)
        result = self.run_script(
            "middaycommander-release.sh",
            "--tag",
            "v9.9.9",
            extra_env={"PATH": f"{test_path}:/usr/bin:/bin:/usr/sbin:/sbin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required command: goreleaser", result.stderr)


if __name__ == "__main__":
    unittest.main()
