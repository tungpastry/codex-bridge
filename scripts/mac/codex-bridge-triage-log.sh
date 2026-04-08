#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${1:-}" ]]; then
  echo "Usage: $0 <systemd-service-name>" >&2
  exit 1
fi

SERVICE_NAME="$1"
BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"
RUNTIME_HOST="${CODEX_BRIDGE_RUNTIME_SSH_HOST:-UbuntuServer}"
REPO_NAME="${CODEX_BRIDGE_DEFAULT_REPO:-MiddayCommander}"
LOG_TEXT="$(ssh "$RUNTIME_HOST" "journalctl -u '$SERVICE_NAME' -n 200 --no-pager" || true)"

jq -n \
  --arg service "$SERVICE_NAME" \
  --arg log_text "$LOG_TEXT" \
  --arg repo "$REPO_NAME" \
  '{service:$service, log_text:$log_text, repo:$repo, source:"mac-script"}' \
  | curl -fsS "${BASE_URL}/v1/summarize/log" \
      -H "Content-Type: application/json" \
      -d @- | jq .
