#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${1:-}" ]]; then
  echo "Usage: $0 <repo-path>" >&2
  exit 1
fi

REPO_PATH="$1"
BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"
REPO_NAME="$(basename "$REPO_PATH")"
DIFF_TEXT="$(git -C "$REPO_PATH" diff main...HEAD)"

jq -n \
  --arg repo "$REPO_NAME" \
  --arg diff_text "$DIFF_TEXT" \
  '{repo:$repo, diff_text:$diff_text, base_ref:"main", head_ref:"HEAD"}' \
  | curl -fsS "${BASE_URL}/v1/summarize/diff" \
      -H "Content-Type: application/json" \
      -d @- | jq .
