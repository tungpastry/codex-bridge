from app.execution.adapters.local import run_local_command
from app.execution.adapters.ssh import run_ssh_command

__all__ = ["run_local_command", "run_ssh_command"]
