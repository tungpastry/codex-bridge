#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/mac/middaycommander-common.sh
source "${SCRIPT_DIR}/middaycommander-common.sh"

usage() {
  cat <<'EOF'
Usage: middaycommander-deploy-router.sh [--dry-run] [--help]

Sync the local codex-bridge source tree from the Mac mini to UbuntuDesktop,
refresh the Python environment, reinstall the systemd unit, restart the
router service, and verify router health on 192.168.1.15.
EOF
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

midday_load_env
midday_require_cmd ssh tar curl jq python3

if [[ ! -d "$MIDDAY_BRIDGE_MAC_ROOT" ]]; then
  echo "Local codex-bridge root not found: $MIDDAY_BRIDGE_MAC_ROOT" >&2
  exit 1
fi

desktop_root_q="$(printf '%q' "$MIDDAY_DESKTOP_BRIDGE_ROOT")"
service_q="$(printf '%q' "$MIDDAY_ROUTER_SERVICE")"

if (( DRY_RUN )); then
  cat <<EOF
## MiddayCommander Router Deploy (dry run)
- Local source: $MIDDAY_BRIDGE_MAC_ROOT
- UbuntuDesktop: $MIDDAY_DESKTOP_SSH
- Desktop root: $MIDDAY_DESKTOP_BRIDGE_ROOT
- Router service: $MIDDAY_ROUTER_SERVICE

Would run:
- tar sync from local codex-bridge to $MIDDAY_DESKTOP_SSH:$MIDDAY_DESKTOP_BRIDGE_ROOT
- ensure virtualenv at $MIDDAY_DESKTOP_BRIDGE_ROOT/.venv
- install requirements.txt
- sudo -n cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service
- sudo -n systemctl daemon-reload
- sudo -n systemctl restart $MIDDAY_ROUTER_SERVICE
- curl -fsS http://127.0.0.1:8787/health
EOF
  exit 0
fi

ssh "$MIDDAY_DESKTOP_SSH" "mkdir -p $desktop_root_q"

tar -C "$MIDDAY_BRIDGE_MAC_ROOT" \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='storage' \
  --exclude='.env' \
  --exclude='targets/*.env' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  -cf - . | ssh "$MIDDAY_DESKTOP_SSH" "tar -xf - -C $desktop_root_q"

refresh_cmd="cd $desktop_root_q && if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi && .venv/bin/pip install -r requirements.txt && sudo -n cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service && sudo -n systemctl daemon-reload && sudo -n systemctl restart $service_q && systemctl is-active $service_q && curl -fsS http://127.0.0.1:8787/health"
remote_output="$(midday_ssh_bash "$MIDDAY_DESKTOP_SSH" "$refresh_cmd" 2>&1)" || {
  echo "Router deploy failed on $MIDDAY_DESKTOP_SSH: $(midday_first_line "$remote_output")" >&2
  printf '%s\n' "$remote_output" >&2
  exit 1
}

health_output="$(curl -fsS "${MIDDAY_ROUTER_BASE_URL}/health" 2>&1)" || {
  echo "Router deploy finished but health check failed at ${MIDDAY_ROUTER_BASE_URL}: $(midday_first_line "$health_output")" >&2
  exit 1
}

printf '%s\n' "$remote_output"
printf '%s\n' "$health_output" | jq .
