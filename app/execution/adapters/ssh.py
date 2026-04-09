from __future__ import annotations

import subprocess


def run_ssh_command(host_alias: str, shell_command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ssh", host_alias, shell_command],
        capture_output=True,
        text=True,
        check=False,
    )
