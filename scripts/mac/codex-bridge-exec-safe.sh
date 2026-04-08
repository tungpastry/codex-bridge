#!/usr/bin/env bash
set -euo pipefail

PLAN_FILE=""
RUN_ID=""
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNS_DIR="${CODEX_BRIDGE_MAC_ROOT:-$ROOT_DIR}/storage/gemini_runs"
RUNTIME_HOST="${CODEX_BRIDGE_RUNTIME_SSH_HOST:-UbuntuServer}"
DESKTOP_HOST="${CODEX_BRIDGE_SSH_HOST:-UbuntuDesktop}"
BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"
ALLOWED_RESTART_SERVICES_RAW="${CODEX_BRIDGE_ALLOWED_RESTART_SERVICES:-codex-bridge,postgresql,nginx}"
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

jq . "$PLAN_FILE" >/dev/null

NEEDS_HUMAN="$(jq -r '.needs_human // false' "$PLAN_FILE")"
if [[ "$NEEDS_HUMAN" == "true" ]]; then
  jq -n \
    --arg run_id "$RUN_ID" \
    --arg status "blocked" \
    --arg reason "$(jq -r '.why // "Gemini requested human escalation."' "$PLAN_FILE")" \
    --arg markdown "$(jq -r '.final_markdown // empty' "$PLAN_FILE")" \
    '{run_id:$run_id, status:$status, reason:$reason, final_markdown:$markdown}' | tee "$RESULT_FILE"
  exit 1
fi

IFS=',' read -r -a RESTART_ALLOWLIST <<<"$ALLOWED_RESTART_SERVICES_RAW"

quote_arg() {
  local value="$1"
  printf "%q" "$value"
}

contains_restart_allowlist() {
  local needle="$1"
  local item
  for item in "${RESTART_ALLOWLIST[@]}"; do
    [[ "$needle" == "$item" ]] && return 0
  done
  return 1
}

host_to_ssh() {
  case "$1" in
    local) echo "" ;;
    UbuntuServer) echo "$RUNTIME_HOST" ;;
    UbuntuDesktop) echo "$DESKTOP_HOST" ;;
    *) return 1 ;;
  esac
}

build_command() {
  local command_id="$1"
  local args_json="$2"
  local url service port repo_path lines
  case "$command_id" in
    router_health)
      echo "curl -fsS $(quote_arg "${BASE_URL}/health")"
      ;;
    http_health)
      url="$(jq -r '.url' <<<"$args_json")"
      [[ "$url" =~ ^https?:// ]] || return 1
      echo "curl -fsS $(quote_arg "$url")"
      ;;
    journalctl_service)
      service="$(jq -r '.service // .service_name // empty' <<<"$args_json")"
      lines="$(jq -r '.lines // 200' <<<"$args_json")"
      [[ "$service" =~ ^[A-Za-z0-9_.@-]+$ ]] || return 1
      [[ "$lines" =~ ^[0-9]+$ ]] || return 1
      (( lines <= 200 )) || return 1
      echo "journalctl -u $(quote_arg "$service") -n $lines --no-pager"
      ;;
    systemctl_status)
      service="$(jq -r '.service // .service_name // empty' <<<"$args_json")"
      [[ "$service" =~ ^[A-Za-z0-9_.@-]+$ ]] || return 1
      echo "systemctl status $(quote_arg "$service") --no-pager"
      ;;
    systemctl_is_active)
      service="$(jq -r '.service // .service_name // empty' <<<"$args_json")"
      [[ "$service" =~ ^[A-Za-z0-9_.@-]+$ ]] || return 1
      echo "systemctl is-active $(quote_arg "$service")"
      ;;
    systemctl_is_failed)
      service="$(jq -r '.service // .service_name // empty' <<<"$args_json")"
      [[ "$service" =~ ^[A-Za-z0-9_.@-]+$ ]] || return 1
      echo "systemctl is-failed $(quote_arg "$service")"
      ;;
    service_restart)
      service="$(jq -r '.service // .service_name // empty' <<<"$args_json")"
      [[ "$service" =~ ^[A-Za-z0-9_.@-]+$ ]] || return 1
      contains_restart_allowlist "$service" || return 1
      echo "systemctl restart $(quote_arg "$service")"
      ;;
    disk_usage)
      echo "df -h"
      ;;
    memory_usage)
      echo "free -h"
      ;;
    uptime)
      echo "uptime"
      ;;
    process_list)
      echo "ps aux | head -n 25"
      ;;
    port_listen)
      port="$(jq -r '.port' <<<"$args_json")"
      [[ "$port" =~ ^[0-9]+$ ]] || return 1
      echo "ss -ltnp '( sport = :$port )'"
      ;;
    git_status)
      repo_path="$(jq -r '.repo_path' <<<"$args_json")"
      [[ -n "$repo_path" ]] || return 1
      echo "git -C $(quote_arg "$repo_path") status --short"
      ;;
    git_diff_main_head)
      repo_path="$(jq -r '.repo_path' <<<"$args_json")"
      [[ -n "$repo_path" ]] || return 1
      echo "git -C $(quote_arg "$repo_path") diff main...HEAD"
      ;;
    git_log_recent)
      repo_path="$(jq -r '.repo_path' <<<"$args_json")"
      [[ -n "$repo_path" ]] || return 1
      echo "git -C $(quote_arg "$repo_path") log --oneline -n 15"
      ;;
    *)
      return 1
      ;;
  esac
}

run_on_host() {
  local host="$1"
  local shell_command="$2"
  local ssh_alias
  ssh_alias="$(host_to_ssh "$host")"
  if [[ -z "$ssh_alias" ]]; then
    bash -lc "$shell_command"
  else
    ssh "$ssh_alias" "$shell_command"
  fi
}

results='[]'
count="$(jq '.commands | length' "$PLAN_FILE")"

for ((i=0; i<count; i++)); do
  command_json="$(jq -c ".commands[$i]" "$PLAN_FILE")"
  host="$(jq -r '.host' <<<"$command_json")"
  command_id="$(jq -r '.command_id' <<<"$command_json")"
  reason="$(jq -r '.reason // empty' <<<"$command_json")"
  args_json="$(jq -c '.args // {}' <<<"$command_json")"

  case "$host" in
    local|UbuntuDesktop|UbuntuServer) ;;
    *)
      jq -n \
        --arg run_id "$RUN_ID" \
        --arg status "blocked" \
        --arg reason "Invalid or forbidden host: ${host}" \
        --arg markdown "$(jq -r '.final_markdown // empty' "$PLAN_FILE")" \
        '{run_id:$run_id, status:$status, reason:$reason, final_markdown:$markdown}' | tee "$RESULT_FILE"
      exit 1
      ;;
  esac

  shell_command="$(build_command "$command_id" "$args_json" || true)"
  if [[ -z "$shell_command" ]]; then
    jq -n \
      --arg run_id "$RUN_ID" \
      --arg status "blocked" \
      --arg reason "Invalid or forbidden command: ${command_id}" \
      --arg markdown "$(jq -r '.final_markdown // empty' "$PLAN_FILE")" \
      '{run_id:$run_id, status:$status, reason:$reason, final_markdown:$markdown}' | tee "$RESULT_FILE"
    exit 1
  fi

  output="$(run_on_host "$host" "$shell_command" 2>&1 || true)"
  results="$(jq -c \
    --arg host "$host" \
    --arg command_id "$command_id" \
    --arg reason "$reason" \
    --arg shell_command "$shell_command" \
    --arg output "$output" \
    '. + [{host:$host, command_id:$command_id, reason:$reason, shell_command:$shell_command, output:$output}]' <<<"$results")"
done

jq -n \
  --arg run_id "$RUN_ID" \
  --arg status "ok" \
  --arg summary "$(jq -r '.summary // empty' "$PLAN_FILE")" \
  --arg confidence "$(jq -r '.confidence // empty' "$PLAN_FILE")" \
  --arg why "$(jq -r '.why // empty' "$PLAN_FILE")" \
  --arg final_markdown "$(jq -r '.final_markdown // empty' "$PLAN_FILE")" \
  --argjson results "$results" \
  '{run_id:$run_id, status:$status, summary:$summary, confidence:$confidence, why:$why, final_markdown:$final_markdown, results:$results}' \
  | tee "$RESULT_FILE"
