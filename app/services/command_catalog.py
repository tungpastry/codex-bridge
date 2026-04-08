from __future__ import annotations

from typing import Dict, List


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

COMMAND_CATALOG: Dict[str, Dict[str, object]] = {
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


def allowed_command_ids() -> List[str]:
    return sorted(COMMAND_CATALOG.keys())


def validate_command_spec(command: dict, allowed_restart_services: List[str]) -> List[str]:
    errors: List[str] = []

    host = command.get("host")
    command_id = command.get("command_id")
    args = command.get("args") or {}

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
            errors.append("missing_arg:{0}".format(key))

    if command_id == "journalctl_service":
        lines = int(args.get("lines", 200)) if str(args.get("lines", "200")).isdigit() else 200
        if lines > 200:
            errors.append("journalctl_line_limit_exceeded")

    if command_id == "service_restart":
        service = str(args.get("service", "")).strip()
        if service not in allowed_restart_services:
            errors.append("service_restart_not_allowed")

    return errors
