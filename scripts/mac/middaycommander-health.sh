#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/mac/middaycommander-common.sh
source "${SCRIPT_DIR}/middaycommander-common.sh"

usage() {
  cat <<'EOF'
Usage: middaycommander-health.sh [--dry-run] [--help]

Check the MiddayCommander three-node topology:
- router health from the Mac mini
- codex-bridge.service and local router health on UbuntuDesktop
- MiddayCommander repo presence, branch, head, and worktree cleanliness on UbuntuServer
- promoted MiddayCommander release state on UbuntuServer
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
midday_require_cmd curl jq ssh

if (( DRY_RUN )); then
  cat <<EOF
## Router
- URL: $MIDDAY_ROUTER_BASE_URL
- Reachable: dry-run

## UbuntuDesktop
- SSH: $MIDDAY_DESKTOP_SSH
- Router service: $MIDDAY_ROUTER_SERVICE
- Local health probe: curl -fsS http://127.0.0.1:8787/health

## UbuntuServer
- SSH: $MIDDAY_SERVER_SSH
- Repo root: $MIDDAY_SERVER_ROOT

## MiddayCommander Repo
- Branch: dry-run
- Head: dry-run
- Worktree: dry-run

## MiddayCommander Release
- Release root: $MIDDAY_RELEASES_ROOT
- Root present: dry-run
- Current target: dry-run
- Binary present: dry-run
- Binary version: dry-run

## Open Issues
- None. Dry run only.

## Next Actions
- Run without --dry-run to execute the checks.
EOF
  exit 0
fi

issues=()
actions=()

router_reachable=false
router_service="unknown"
router_status="unknown"
if router_payload="$(curl -fsS "${MIDDAY_ROUTER_BASE_URL}/health" 2>&1)"; then
  router_reachable=true
  router_service="$(printf '%s' "$router_payload" | jq -r '.service // "unknown"' 2>/dev/null || printf 'invalid-json')"
  router_status="$(printf '%s' "$router_payload" | jq -r '.status // "unknown"' 2>/dev/null || printf 'invalid-json')"
  if [[ "$router_status" != "ok" ]]; then
    issues+=("Router health endpoint returned status=${router_status} at ${MIDDAY_ROUTER_BASE_URL}.")
    actions+=("Check codex-bridge logs and service state on UbuntuDesktop.")
  fi
else
  issues+=("Router health endpoint is unreachable at ${MIDDAY_ROUTER_BASE_URL}: $(midday_first_line "$router_payload")")
  actions+=("Confirm codex-bridge.service is listening on 0.0.0.0:8787 and LAN routing is healthy.")
fi

desktop_service_active="unknown"
desktop_local_health="unknown"
desktop_service_ok=false
desktop_health_ok=false
desktop_service_cmd="systemctl is-active $(printf '%q' "$MIDDAY_ROUTER_SERVICE")"
if desktop_service_output="$(midday_ssh_bash "$MIDDAY_DESKTOP_SSH" "$desktop_service_cmd" 2>&1)"; then
  desktop_service_active="$(printf '%s' "$desktop_service_output" | tr -d '\r' | sed -n '1p')"
  if [[ "$desktop_service_active" == "active" ]]; then
    desktop_service_ok=true
  else
    issues+=("UbuntuDesktop reports ${MIDDAY_ROUTER_SERVICE} as ${desktop_service_active}.")
    actions+=("Restart ${MIDDAY_ROUTER_SERVICE} or inspect systemd logs on UbuntuDesktop.")
  fi
else
  issues+=("Failed to check ${MIDDAY_ROUTER_SERVICE} on ${MIDDAY_DESKTOP_SSH}: $(midday_first_line "$desktop_service_output")")
  actions+=("Verify SSH access to UbuntuDesktop and non-interactive sudo.")
fi

if desktop_health_output="$(midday_ssh_bash "$MIDDAY_DESKTOP_SSH" "curl -fsS http://127.0.0.1:8787/health" 2>&1)"; then
  desktop_local_health="$(printf '%s' "$desktop_health_output" | jq -r '.status // "unknown"' 2>/dev/null || printf 'invalid-json')"
  if [[ "$desktop_local_health" == "ok" ]]; then
    desktop_health_ok=true
  else
    issues+=("UbuntuDesktop local router health returned ${desktop_local_health}.")
    actions+=("Inspect the local router process and recent codex-bridge logs on UbuntuDesktop.")
  fi
else
  issues+=("Failed to query local router health on ${MIDDAY_DESKTOP_SSH}: $(midday_first_line "$desktop_health_output")")
  actions+=("Confirm codex-bridge is listening on 127.0.0.1:8787 inside UbuntuDesktop.")
fi

server_repo_present=false
server_repo_git=false
server_branch="unknown"
server_head="unknown"
server_worktree="unknown"
server_status_block=""
server_root_q="$(printf '%q' "$MIDDAY_SERVER_ROOT")"
release_root_present=false
release_current_target="not-promoted"
release_binary_present=false
release_binary_version="unavailable"
release_root_q="$(printf '%q' "$MIDDAY_RELEASES_ROOT")"
release_current_q="$(printf '%q' "$(midday_release_current_path)")"
release_binary_q="$(printf '%q' "$MIDDAY_RELEASE_BINARY_NAME")"

if midday_ssh_bash "$MIDDAY_SERVER_SSH" "[[ -d $server_root_q ]]" >/dev/null 2>&1; then
  server_repo_present=true
else
  issues+=("MiddayCommander repo root is missing on ${MIDDAY_SERVER_SSH}: ${MIDDAY_SERVER_ROOT}")
  actions+=("Restore or clone MiddayCommander under ${MIDDAY_SERVER_ROOT} on UbuntuServer.")
fi

if [[ "$server_repo_present" == "true" ]]; then
  if midday_ssh_bash "$MIDDAY_SERVER_SSH" "git -C $server_root_q rev-parse --is-inside-work-tree >/dev/null 2>&1"; then
    server_repo_git=true
    server_branch="$(midday_ssh_bash "$MIDDAY_SERVER_SSH" "git -C $server_root_q branch --show-current" 2>/dev/null | tr -d '\r' | sed -n '1p')"
    server_head="$(midday_ssh_bash "$MIDDAY_SERVER_SSH" "git -C $server_root_q rev-parse --short HEAD" 2>/dev/null | tr -d '\r' | sed -n '1p')"
    server_status_block="$(midday_ssh_bash "$MIDDAY_SERVER_SSH" "git -C $server_root_q status --short" 2>/dev/null)"
    if [[ -n "$server_status_block" ]]; then
      server_worktree="dirty"
      issues+=("MiddayCommander repo on ${MIDDAY_SERVER_SSH} is dirty.")
      actions+=("Review and clean the server worktree before relying on it for validation.")
    else
      server_worktree="clean"
    fi
  else
    issues+=("MiddayCommander path exists on ${MIDDAY_SERVER_SSH} but is not a git worktree: ${MIDDAY_SERVER_ROOT}")
    actions+=("Repair the MiddayCommander checkout on UbuntuServer.")
  fi
fi

if midday_ssh_bash "$MIDDAY_SERVER_SSH" "[[ -d $release_root_q ]]" >/dev/null 2>&1; then
  release_root_present=true
  release_current_target="$(midday_ssh_bash "$MIDDAY_SERVER_SSH" "if [[ -L $release_current_q ]]; then readlink $release_current_q; elif [[ -e $release_current_q ]]; then echo not-a-symlink; else echo missing; fi" 2>/dev/null | tr -d '\r' | sed -n '1p')"
  if [[ "$release_current_target" == "missing" ]]; then
    issues+=("MiddayCommander release root exists on ${MIDDAY_SERVER_SSH} but current symlink is missing.")
    actions+=("Re-promote a tagged MiddayCommander release to restore the current symlink.")
  elif [[ "$release_current_target" == "not-a-symlink" ]]; then
    issues+=("MiddayCommander current release path on ${MIDDAY_SERVER_SSH} is not a symlink.")
    actions+=("Repair ${MIDDAY_RELEASES_ROOT}/current so it points at a promoted release directory.")
  elif midday_ssh_bash "$MIDDAY_SERVER_SSH" "[[ -x $release_current_q/$release_binary_q ]]"; then
    release_binary_present=true
    if release_version_output="$(midday_ssh_bash "$MIDDAY_SERVER_SSH" "$release_current_q/$release_binary_q --version" 2>&1)"; then
      release_binary_version="$(printf '%s' "$release_version_output" | tr -d '\r' | sed -n '1p')"
    else
      release_binary_version="error"
      issues+=("Promoted MiddayCommander binary exists on ${MIDDAY_SERVER_SSH} but --version failed: $(midday_first_line "$release_version_output")")
      actions+=("Inspect the promoted binary under ${MIDDAY_RELEASES_ROOT}/current and re-promote if needed.")
    fi
  else
    issues+=("MiddayCommander current release on ${MIDDAY_SERVER_SSH} is missing ${MIDDAY_RELEASE_BINARY_NAME}.")
    actions+=("Repair or re-promote the current MiddayCommander release on UbuntuServer.")
  fi
fi

if [[ "${#actions[@]}" -eq 0 ]]; then
  actions+=("Continue normal MiddayCommander development and health verification.")
fi

echo "## Router"
echo "- URL: ${MIDDAY_ROUTER_BASE_URL}"
echo "- Reachable: $(midday_markdown_bool "$router_reachable")"
echo "- Service: ${router_service}"
echo "- Status: ${router_status}"
echo
echo "## UbuntuDesktop"
echo "- SSH: ${MIDDAY_DESKTOP_SSH}"
echo "- Router service: ${MIDDAY_ROUTER_SERVICE}"
echo "- Service active: ${desktop_service_active}"
echo "- Local health: ${desktop_local_health}"
echo
echo "## UbuntuServer"
echo "- SSH: ${MIDDAY_SERVER_SSH}"
echo "- Repo root: ${MIDDAY_SERVER_ROOT}"
echo "- Repo present: $(midday_markdown_bool "$server_repo_present")"
echo
echo "## MiddayCommander Repo"
echo "- Branch: ${server_branch:-unknown}"
echo "- Head: ${server_head:-unknown}"
echo "- Worktree: ${server_worktree}"
if [[ -n "$server_status_block" ]]; then
  echo
  echo '```text'
  printf '%s\n' "$server_status_block"
  echo '```'
fi
echo
echo "## MiddayCommander Release"
echo "- Release root: ${MIDDAY_RELEASES_ROOT}"
echo "- Root present: $(midday_markdown_bool "$release_root_present")"
echo "- Current target: ${release_current_target}"
echo "- Binary present: $(midday_markdown_bool "$release_binary_present")"
echo "- Binary version: ${release_binary_version}"
echo
echo "## Open Issues"
if [[ "${#issues[@]}" -eq 0 ]]; then
  echo "- None"
else
  for item in "${issues[@]}"; do
    echo "- $item"
  done
fi
echo
echo "## Next Actions"
for item in "${actions[@]}"; do
  echo "- $item"
done

if [[ "${#issues[@]}" -gt 0 ]]; then
  exit 1
fi
