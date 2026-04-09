from __future__ import annotations

from typing import Any

from app.schemas.execution import ExecutionCommand


ALLOWED_HOSTS = ("local", "UbuntuDesktop", "UbuntuServer")
FORBIDDEN_TOKENS = (
    "sudo",
    " rm ",
    " mv ",
    " chmod ",
    " chown ",
    "git push",
    "git reset",
    "docker",
    "kubectl",
    "psql",
    "alembic upgrade",
    "systemctl stop",
    "systemctl disable",
    "firewall",
    "rotate secret",
    "auth change",
)

COMMAND_CATALOG: dict[str, dict[str, object]] = {
    "router_health": {"required_args": [], "description": "GET router health endpoint"},
    "http_health": {"required_args": ["url"], "description": "GET arbitrary health URL"},
    "journalctl_service": {"required_args": ["service"], "description": "Read recent journalctl lines"},
    "systemctl_status": {"required_args": ["service"], "description": "Read systemctl status"},
    "systemctl_is_active": {"required_args": ["service"], "description": "Read systemctl active state"},
    "systemctl_is_failed": {"required_args": ["service"], "description": "Read systemctl failed state"},
    "service_restart": {"required_args": ["service"], "description": "Restart allowlisted service"},
    "disk_usage": {"required_args": [], "description": "Read disk usage"},
    "memory_usage": {"required_args": [], "description": "Read memory usage"},
    "uptime": {"required_args": [], "description": "Read uptime"},
    "process_list": {"required_args": [], "description": "Read top processes"},
    "port_listen": {"required_args": ["port"], "description": "Read listening port state"},
    "git_status": {"required_args": ["repo_path"], "description": "Read git status"},
    "git_diff_main_head": {"required_args": ["repo_path"], "description": "Read git diff main...HEAD"},
    "git_log_recent": {"required_args": ["repo_path"], "description": "Read recent git log"},
}


def allowed_command_ids() -> list[str]:
    return sorted(COMMAND_CATALOG.keys())


def validate_command_spec(command: dict[str, Any] | ExecutionCommand, allowed_restart_services: list[str]) -> list[str]:
    if isinstance(command, ExecutionCommand):
        payload = command.model_dump()
    else:
        payload = command

    errors: list[str] = []
    host = payload.get("host")
    command_id = payload.get("command_id")
    args = payload.get("args") or {}

    if host not in ALLOWED_HOSTS:
        errors.append("host_not_allowed")
    if command_id not in COMMAND_CATALOG:
        errors.append("command_id_not_allowed")
        return errors
    if not isinstance(args, dict):
        errors.append("args_must_be_object")
        return errors

    required_args = COMMAND_CATALOG[command_id]["required_args"]
    for key in required_args:
        if key not in args or args.get(key) in ("", None):
            errors.append(f"missing_arg:{key}")

    if command_id == "journalctl_service":
        lines = int(args.get("lines", 200)) if str(args.get("lines", "200")).isdigit() else 200
        if lines > 200:
            errors.append("journalctl_line_limit_exceeded")

    if command_id == "service_restart":
        service = str(args.get("service", "")).strip()
        if service not in allowed_restart_services:
            errors.append("service_restart_not_allowed")

    return errors


def build_shell_command(
    command_id: str,
    args: dict[str, Any],
    *,
    base_url: str,
    allowed_restart_services: list[str],
) -> str | None:
    def _q(value: Any) -> str:
        import shlex

        return shlex.quote(str(value))

    if command_id == "router_health":
        return f"curl -fsS {_q(base_url + '/health')}"
    if command_id == "http_health":
        url = str(args.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            return None
        return f"curl -fsS {_q(url)}"
    if command_id == "journalctl_service":
        service = str(args.get("service") or args.get("service_name") or "").strip()
        lines = str(args.get("lines", 200)).strip()
        if not service or not lines.isdigit() or int(lines) > 200:
            return None
        return f"journalctl -u {_q(service)} -n {int(lines)} --no-pager"
    if command_id == "systemctl_status":
        service = str(args.get("service") or args.get("service_name") or "").strip()
        return f"systemctl status {_q(service)} --no-pager" if service else None
    if command_id == "systemctl_is_active":
        service = str(args.get("service") or args.get("service_name") or "").strip()
        return f"systemctl is-active {_q(service)}" if service else None
    if command_id == "systemctl_is_failed":
        service = str(args.get("service") or args.get("service_name") or "").strip()
        return f"systemctl is-failed {_q(service)}" if service else None
    if command_id == "service_restart":
        service = str(args.get("service") or args.get("service_name") or "").strip()
        if not service or service not in allowed_restart_services:
            return None
        return f"systemctl restart {_q(service)}"
    if command_id == "disk_usage":
        return "df -h"
    if command_id == "memory_usage":
        return "free -h"
    if command_id == "uptime":
        return "uptime"
    if command_id == "process_list":
        return "ps aux | head -n 25"
    if command_id == "port_listen":
        port = str(args.get("port", "")).strip()
        if not port.isdigit():
            return None
        return f"ss -ltnp '( sport = :{port} )'"
    if command_id == "git_status":
        repo_path = str(args.get("repo_path", "")).strip()
        return f"git -C {_q(repo_path)} status --short" if repo_path else None
    if command_id == "git_diff_main_head":
        repo_path = str(args.get("repo_path", "")).strip()
        return f"git -C {_q(repo_path)} diff main...HEAD" if repo_path else None
    if command_id == "git_log_recent":
        repo_path = str(args.get("repo_path", "")).strip()
        return f"git -C {_q(repo_path)} log --oneline -n 15" if repo_path else None
    return None
