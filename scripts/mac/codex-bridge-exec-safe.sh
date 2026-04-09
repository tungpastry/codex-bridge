#!/usr/bin/env bash
set -euo pipefail

PLAN_FILE=""
RUN_ID=""
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python3"
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi
RUNS_DIR="${CODEX_BRIDGE_MAC_ROOT:-$ROOT_DIR}/storage/gemini_runs"
mkdir -p "$RUNS_DIR"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan-file)
      PLAN_FILE="${2:-}"
      shift 2
      ;;
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    *)
      echo "Usage: $0 --plan-file <gemini-plan.json> [--run-id <run-id>]" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PLAN_FILE" ]]; then
  echo "Usage: $0 --plan-file <gemini-plan.json> [--run-id <run-id>]" >&2
  exit 1
fi

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
fi

RESULT_FILE="${RUNS_DIR}/${RUN_ID}-exec-results.json"
exec "$PYTHON_BIN" -m app.execution.cli run-plan \
  --plan-file "$PLAN_FILE" \
  --run-id "$RUN_ID" \
  --result-file "$RESULT_FILE" \
  --runs-dir "$RUNS_DIR"
