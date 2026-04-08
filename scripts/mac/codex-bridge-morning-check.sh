#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"
RUNTIME_HOST="${CODEX_BRIDGE_RUNTIME_SSH_HOST:-UbuntuServer}"
SERVICES_RAW="${CODEX_BRIDGE_MORNING_SERVICES:-postgresql cron ssh}"

echo "## Router Health"
curl -fsS "${BASE_URL}/health" | jq .
echo
echo "## Runtime Services"

for service in $SERVICES_RAW; do
  state="$(ssh "$RUNTIME_HOST" "systemctl is-active '$service' 2>/dev/null || true")"
  failed_state="$(ssh "$RUNTIME_HOST" "systemctl is-failed '$service' 2>/dev/null || true")"
  case "$failed_state" in
    failed) failed="yes" ;;
    active|inactive) failed="no" ;;
    *) failed="${failed_state:-unknown}" ;;
  esac
  echo "- ${service}: active=${state:-unknown} failed=${failed:-unknown}"
done
