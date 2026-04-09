from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.execution.callback_client import build_callback_payload, post_execution_callback
from app.execution.runner import execute_plan
from app.schemas.execution import ExecutionPlan
from app.utils.files import write_json


def _parse_services(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def run_plan_command(args: argparse.Namespace) -> int:
    plan = ExecutionPlan.model_validate_json(Path(args.plan_file).read_text(encoding="utf-8"))
    runs_dir = Path(args.runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    result = execute_plan(
        plan,
        run_id=args.run_id,
        runs_dir=runs_dir,
        base_url=args.base_url,
        runtime_host=args.runtime_host,
        desktop_host=args.desktop_host,
        allowed_restart_services=_parse_services(args.allowed_restart_services),
    )
    write_json(Path(args.result_file), result.model_dump())
    print(json.dumps(result.model_dump(), ensure_ascii=False))
    return 0 if result.status == "ok" else 1


def post_callback_command(args: argparse.Namespace) -> int:
    payload_dict = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    payload = build_callback_payload(
        run_id=args.run_id,
        final_payload=payload_dict,
        artifact_files=[
            ("gemini_job", args.job_file),
            ("execution_plan", args.plan_file),
            ("execution_result", args.exec_output_file),
            ("timing", args.timing_file),
            ("final_result", args.final_output_file),
        ],
    )
    post_execution_callback(
        base_url=args.base_url,
        run_id=args.run_id,
        token=args.token,
        payload=payload,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="codex-bridge execution helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_plan = subparsers.add_parser("run-plan")
    run_plan.add_argument("--plan-file", required=True)
    run_plan.add_argument("--run-id", required=True)
    run_plan.add_argument("--result-file", required=True)
    run_plan.add_argument("--runs-dir", required=True)
    run_plan.add_argument("--base-url", default=os.environ.get("CODEX_BRIDGE_BASE_URL", "http://192.168.1.15:8787"))
    run_plan.add_argument("--runtime-host", default=os.environ.get("CODEX_BRIDGE_RUNTIME_SSH_HOST", "UbuntuServer"))
    run_plan.add_argument("--desktop-host", default=os.environ.get("CODEX_BRIDGE_SSH_HOST", "UbuntuDesktop"))
    run_plan.add_argument(
        "--allowed-restart-services",
        default=os.environ.get("CODEX_BRIDGE_ALLOWED_RESTART_SERVICES", "codex-bridge,postgresql,nginx"),
    )
    run_plan.set_defaults(func=run_plan_command)

    callback = subparsers.add_parser("post-callback")
    callback.add_argument("--run-id", required=True)
    callback.add_argument("--payload-file", required=True)
    callback.add_argument("--job-file", required=True)
    callback.add_argument("--plan-file", required=True)
    callback.add_argument("--exec-output-file", required=True)
    callback.add_argument("--timing-file", required=True)
    callback.add_argument("--final-output-file", required=True)
    callback.add_argument("--base-url", default=os.environ.get("CODEX_BRIDGE_BASE_URL", "http://192.168.1.15:8787"))
    callback.add_argument("--token", default=os.environ.get("CODEX_BRIDGE_INTERNAL_API_TOKEN", ""))
    callback.set_defaults(func=post_callback_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
