from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.profiles.loader import load_profiles
from tests.helpers import temporary_client


class ProfileValidationTestCase(unittest.TestCase):
    def test_profile_missing_required_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "broken.yaml"
            profile_path.write_text("default_safe_services:\n  - codex-bridge\n", encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_profiles(Path(temp_dir))

    def test_profile_wrong_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "broken.yaml"
            profile_path.write_text(
                "repo_name: codex-bridge\ndefault_safe_services: codex-bridge\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                load_profiles(Path(temp_dir))

    def test_valid_profile_does_not_weaken_safety(self) -> None:
        with temporary_client() as (client, _temp_root):
            response = client.post(
                "/v1/dispatch/task",
                json={
                    "title": "Dangerous production change",
                    "input_kind": "task",
                    "context": "Drop table in production and rotate secret immediately.",
                    "repo": "MiddayCommander",
                    "source": "test",
                    "constraints": [],
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["route"], "human")

    def test_hidden_appledouble_yaml_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "codex-bridge.yaml").write_text(
                "repo_name: codex-bridge\ndefault_safe_services:\n  - codex-bridge\n",
                encoding="utf-8",
            )
            (temp_path / "._codex-bridge.yaml").write_bytes(b"\x00\xa3not-utf8-yaml")
            profiles = load_profiles(temp_path)
            self.assertIn("codex-bridge", profiles)

    def test_codex_bridge_profile_prefers_desktop_for_service_commands(self) -> None:
        profiles = load_profiles(Path(__file__).resolve().parents[1] / "app" / "profiles")
        profile = profiles["codex-bridge"]
        self.assertEqual(profile.preferred_command_hosts["journalctl_service"], "UbuntuDesktop")
        self.assertEqual(profile.preferred_command_hosts["systemctl_status"], "UbuntuDesktop")
