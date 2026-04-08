#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${1:-}" || -z "${2:-}" || -z "${3:-}" || -z "${4:-}" ]]; then
  echo "Usage: $0 <input-kind> <title> <repo> <context-file>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_KIND="$1"
TITLE="$2"
REPO="$3"
CONTEXT_FILE="$4"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
DISPATCH_FILE="${TMP_DIR}/dispatch.json"
JOB_FILE="${TMP_DIR}/gemini-job.json"

"${ROOT_DIR}/scripts/mac/codex-bridge-dispatch.sh" "$INPUT_KIND" "$TITLE" "$REPO" "$CONTEXT_FILE" >"$DISPATCH_FILE"

ROUTE="$(jq -r '.route' "$DISPATCH_FILE")"
case "$ROUTE" in
  codex)
    jq -r '.codex_brief_markdown' "$DISPATCH_FILE"
    ;;
  gemini)
    jq '.gemini_job' "$DISPATCH_FILE" >"$JOB_FILE"
    "${ROOT_DIR}/scripts/mac/codex-bridge-run-gemini.sh" --job-file "$JOB_FILE"
    ;;
  human)
    jq -n \
      --arg route "$ROUTE" \
      --arg block_reason "$(jq -r '.block_reason // empty' "$DISPATCH_FILE")" \
      --arg human_summary "$(jq -r '.human_summary // empty' "$DISPATCH_FILE")" \
      '{route:$route, block_reason:$block_reason, human_summary:$human_summary}'
    exit 1
    ;;
  local)
    jq -r '.local_summary // .problem_summary' "$DISPATCH_FILE"
    ;;
  *)
    echo "Unknown dispatch route: $ROUTE" >&2
    exit 1
    ;;
esac
