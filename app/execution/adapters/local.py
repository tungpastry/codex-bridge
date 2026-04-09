from __future__ import annotations

import subprocess


def run_local_command(shell_command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", "-lc", shell_command],
        capture_output=True,
        text=True,
        check=False,
    )
