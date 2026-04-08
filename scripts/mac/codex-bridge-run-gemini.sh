#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

load_env_value() {
  local key="$1"
  local line=""
  local value=""

  [[ -f "$ENV_FILE" ]] || return 1

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    [[ "${line#\#}" == "$line" ]] || continue
    if [[ "$line" == "${key}="* ]]; then
      value="${line#*=}"
      if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
        value="${value:1:-1}"
      fi
      printf '%s' "$value"
      return 0
    fi
  done <"$ENV_FILE"

  return 1
}

if [[ -z "${CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS:-}" ]]; then
  CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS="$(load_env_value CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS || true)"
fi

GEMINI_BIN="${CODEX_BRIDGE_GEMINI_BIN:-/opt/homebrew/bin/gemini}"
RUNS_DIR="${CODEX_BRIDGE_MAC_ROOT:-$ROOT_DIR}/storage/gemini_runs"
GEMINI_TIMEOUT_SECONDS_RAW="${CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS:-180}"
if [[ "$GEMINI_TIMEOUT_SECONDS_RAW" =~ ^[0-9]+$ ]]; then
  GEMINI_TIMEOUT_SECONDS="$GEMINI_TIMEOUT_SECONDS_RAW"
else
  GEMINI_TIMEOUT_SECONDS=180
fi

# Non-interactive SSH sessions on macOS often skip Homebrew PATH setup.
if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:${PATH}"

mkdir -p "$RUNS_DIR"

MODE="${1:-}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
JOB_FILE="${TMP_DIR}/gemini-job.json"
PROMPT_FILE="${TMP_DIR}/gemini-prompt.txt"
RAW_OUTPUT_FILE="${TMP_DIR}/gemini-raw-output.json"
PLAN_OUTPUT_FILE="${TMP_DIR}/gemini-plan.json"
EXEC_OUTPUT_FILE="${TMP_DIR}/gemini-exec-output.json"
BASE_RESULT_FILE="${TMP_DIR}/gemini-base-result.json"
TIMING_FILE=""
FINAL_OUTPUT_FILE=""

pipeline_started_at=""
pipeline_started_ms=""
pipeline_started_stamp=""
gemini_started_at=""
gemini_started_ms=""
gemini_started_stamp=""
gemini_finished_at=""
gemini_finished_ms=""
gemini_finished_stamp=""
exec_started_at=""
exec_started_ms=""
exec_started_stamp=""
exec_finished_at=""
exec_finished_ms=""
exec_finished_stamp=""
finished_at=""
finished_ms=""
finished_stamp=""
gemini_cli_duration_ms=0
exec_duration_ms=0
total_duration_ms=0
JOB_ID=""
RUN_ID=""
ACTIVE_CHILD_PID=""
ACTIVE_PHASE=""
FINAL_OUTPUT_EMITTED=0
GEMINI_TIMEOUT_FLAG_FILE="${TMP_DIR}/gemini-timeout.flag"

cleanup_tmp_dir() {
  rm -rf "$TMP_DIR"
}

trap cleanup_tmp_dir EXIT

capture_time_vars() {
  local prefix="$1"
  local captured_at=""
  local captured_ms=""
  local captured_stamp=""

  IFS=' ' read -r captured_at captured_ms captured_stamp < <(
    python3 -c 'from datetime import datetime, timezone; now = datetime.now(timezone.utc); print(now.strftime("%Y-%m-%dT%H:%M:%SZ"), int(now.timestamp() * 1000), now.strftime("%Y%m%dT%H%M%SZ"))'
  )

  printf -v "${prefix}_at" '%s' "$captured_at"
  printf -v "${prefix}_ms" '%s' "$captured_ms"
  printf -v "${prefix}_stamp" '%s' "$captured_stamp"
}

format_duration_seconds() {
  python3 -c 'import sys; print(f"{int(sys.argv[1]) / 1000:.1f}s")' "${1:-0}"
}

build_timing_json() {
  jq -n \
    --arg pipeline_started_at "${pipeline_started_at:-}" \
    --arg gemini_started_at "${gemini_started_at:-}" \
    --arg gemini_finished_at "${gemini_finished_at:-}" \
    --arg exec_started_at "${exec_started_at:-}" \
    --arg exec_finished_at "${exec_finished_at:-}" \
    --arg finished_at "${finished_at:-}" \
    --argjson gemini_cli_duration_ms "${gemini_cli_duration_ms:-0}" \
    --argjson exec_duration_ms "${exec_duration_ms:-0}" \
    --argjson total_duration_ms "${total_duration_ms:-0}" \
    '
    def blank_to_null:
      if . == "" then null else . end;
    {
      pipeline_started_at: ($pipeline_started_at | blank_to_null),
      gemini_started_at: ($gemini_started_at | blank_to_null),
      gemini_finished_at: ($gemini_finished_at | blank_to_null),
      exec_started_at: ($exec_started_at | blank_to_null),
      exec_finished_at: ($exec_finished_at | blank_to_null),
      finished_at: ($finished_at | blank_to_null),
      gemini_cli_duration_ms: $gemini_cli_duration_ms,
      exec_duration_ms: $exec_duration_ms,
      total_duration_ms: $total_duration_ms
    }'
}

append_timing_markdown() {
  local markdown="${1:-}"
  local gemini_display="$2"
  local exec_display="$3"
  local total_display="$4"

  if [[ -n "$markdown" ]]; then
    printf '%s\n\n## Timing\n- Gemini CLI headless: %s\n- Safe command execution: %s\n- Total pipeline: %s\n' \
      "$markdown" "$gemini_display" "$exec_display" "$total_display"
  else
    printf '## Timing\n- Gemini CLI headless: %s\n- Safe command execution: %s\n- Total pipeline: %s\n' \
      "$gemini_display" "$exec_display" "$total_display"
  fi
}

write_blocked_result_json() {
  local reason="$1"
  local summary="${2:-Gemini automation blocked.}"
  local confidence="${3:-low}"
  local markdown="${4:-}"

  if [[ -z "$markdown" ]]; then
    markdown="### Gemini Runner Status

${reason}"
  fi

  jq -n \
    --arg status "blocked" \
    --arg summary "$summary" \
    --arg confidence "$confidence" \
    --arg why "$reason" \
    --arg final_markdown "$markdown" \
    '{status:$status, summary:$summary, confidence:$confidence, why:$why, final_markdown:$final_markdown, results:[]}' >"$BASE_RESULT_FILE"
}

emit_final_output() {
  local exit_code="$1"
  local timing_json=""
  local timing_summary=""
  local final_markdown=""
  local gemini_display=""
  local exec_display=""
  local total_display=""

  if [[ "$FINAL_OUTPUT_EMITTED" -eq 1 ]]; then
    return "$exit_code"
  fi
  FINAL_OUTPUT_EMITTED=1

  capture_time_vars finished

  if [[ -n "${gemini_started_ms:-}" && -n "${gemini_finished_ms:-}" ]]; then
    gemini_cli_duration_ms=$((gemini_finished_ms - gemini_started_ms))
  else
    gemini_cli_duration_ms=0
  fi

  if [[ -n "${exec_started_ms:-}" && -n "${exec_finished_ms:-}" ]]; then
    exec_duration_ms=$((exec_finished_ms - exec_started_ms))
  else
    exec_duration_ms=0
  fi

  if [[ -n "${pipeline_started_ms:-}" && -n "${finished_ms:-}" ]]; then
    total_duration_ms=$((finished_ms - pipeline_started_ms))
  else
    total_duration_ms=0
  fi

  timing_json="$(build_timing_json)"
  printf '%s\n' "$timing_json" >"$TIMING_FILE"

  gemini_display="$(format_duration_seconds "$gemini_cli_duration_ms")"
  exec_display="$(format_duration_seconds "$exec_duration_ms")"
  total_display="$(format_duration_seconds "$total_duration_ms")"
  timing_summary="Gemini CLI: ${gemini_display} | Safe exec: ${exec_display} | Total: ${total_display}"
  final_markdown="$(append_timing_markdown "$(jq -r '.final_markdown // empty' "$BASE_RESULT_FILE")" "$gemini_display" "$exec_display" "$total_display")"

  jq \
    --arg run_id "$RUN_ID" \
    --arg job_id "$JOB_ID" \
    --arg timing_summary "$timing_summary" \
    --arg final_markdown "$final_markdown" \
    --argjson timing "$timing_json" \
    '. + {
      run_id: $run_id,
      job_id: $job_id,
      timing_summary: $timing_summary,
      timing: $timing,
      final_markdown: $final_markdown
    }' "$BASE_RESULT_FILE" | tee "$FINAL_OUTPUT_FILE"

  return "$exit_code"
}

run_gemini_cli() {
  local prompt_text="$1"
  local exit_code=0
  local watchdog_pid=""

  rm -f "$GEMINI_TIMEOUT_FLAG_FILE"
  ACTIVE_PHASE="gemini_headless"
  "$GEMINI_BIN" -p "$prompt_text" --output-format json >"$RAW_OUTPUT_FILE" 2>&1 &
  ACTIVE_CHILD_PID="$!"

  if (( GEMINI_TIMEOUT_SECONDS > 0 )); then
    (
      sleep "$GEMINI_TIMEOUT_SECONDS"
      if kill -0 "$ACTIVE_CHILD_PID" 2>/dev/null; then
        : >"$GEMINI_TIMEOUT_FLAG_FILE"
        kill -TERM "$ACTIVE_CHILD_PID" 2>/dev/null || true
        sleep 2
        kill -KILL "$ACTIVE_CHILD_PID" 2>/dev/null || true
      fi
    ) &
    watchdog_pid="$!"
  fi

  if wait "$ACTIVE_CHILD_PID"; then
    exit_code=0
  else
    exit_code="$?"
  fi

  ACTIVE_CHILD_PID=""
  ACTIVE_PHASE=""

  if [[ -n "$watchdog_pid" ]]; then
    kill "$watchdog_pid" >/dev/null 2>&1 || true
    wait "$watchdog_pid" >/dev/null 2>&1 || true
  fi

  return "$exit_code"
}

run_exec_safe() {
  local exit_code=0

  ACTIVE_PHASE="safe_exec"
  "${ROOT_DIR}/scripts/mac/codex-bridge-exec-safe.sh" --plan-file "$PLAN_OUTPUT_FILE" --run-id "$RUN_ID" >"$EXEC_OUTPUT_FILE" 2>&1 &
  ACTIVE_CHILD_PID="$!"

  if wait "$ACTIVE_CHILD_PID"; then
    exit_code=0
  else
    exit_code="$?"
  fi

  ACTIVE_CHILD_PID=""
  ACTIVE_PHASE=""
  return "$exit_code"
}

handle_interrupt() {
  local signal="$1"
  local reason=""
  local exit_code=1

  trap - TERM INT

  case "$signal" in
    INT) exit_code=130 ;;
    TERM) exit_code=143 ;;
  esac

  if [[ -n "$ACTIVE_CHILD_PID" ]]; then
    kill -TERM "$ACTIVE_CHILD_PID" >/dev/null 2>&1 || true
    wait "$ACTIVE_CHILD_PID" >/dev/null 2>&1 || true
    ACTIVE_CHILD_PID=""
  fi

  case "$ACTIVE_PHASE" in
    gemini_headless)
      if [[ -n "${gemini_started_ms:-}" && -z "${gemini_finished_at:-}" ]]; then
        capture_time_vars gemini_finished
      fi
      reason="Gemini runner interrupted by ${signal} during Gemini CLI execution."
      ;;
    safe_exec)
      if [[ -n "${exec_started_ms:-}" && -z "${exec_finished_at:-}" ]]; then
        capture_time_vars exec_finished
      fi
      reason="Gemini runner interrupted by ${signal} during safe command execution."
      ;;
    *)
      reason="Gemini runner interrupted by ${signal}."
      ;;
  esac

  write_blocked_result_json \
    "$reason" \
    "Gemini automation interrupted before completion." \
    "low"
  emit_final_output "$exit_code"
  exit $?
}

trap 'handle_interrupt TERM' TERM
trap 'handle_interrupt INT' INT

case "$MODE" in
  --job-file)
    cp "${2:?missing job file}" "$JOB_FILE"
    ;;
  --stdin-json)
    cat >"$JOB_FILE"
    ;;
  *)
    echo "Usage: $0 --job-file <gemini-job.json> | --stdin-json" >&2
    exit 1
    ;;
esac

capture_time_vars pipeline_started
RUN_ID="${pipeline_started_stamp}"
JOB_ID="$RUN_ID"
TIMING_FILE="${RUNS_DIR}/${RUN_ID}-timing.json"
FINAL_OUTPUT_FILE="${RUNS_DIR}/${RUN_ID}-final.json"

if ! jq . "$JOB_FILE" >/dev/null 2>&1; then
  cp "$JOB_FILE" "${RUNS_DIR}/${RUN_ID}-job.json"
  write_blocked_result_json \
    "Gemini job file is not valid JSON." \
    "Gemini automation stopped before model execution." \
    "low"
  emit_final_output 1
  exit $?
fi

JOB_ID="$(jq -r '.job_id // empty' "$JOB_FILE")"
RUN_ID="${JOB_ID:-$RUN_ID}"
JOB_ID="${JOB_ID:-$RUN_ID}"
TIMING_FILE="${RUNS_DIR}/${RUN_ID}-timing.json"
FINAL_OUTPUT_FILE="${RUNS_DIR}/${RUN_ID}-final.json"

jq -r '.prompt // empty' "$JOB_FILE" >"$PROMPT_FILE"
cp "$JOB_FILE" "${RUNS_DIR}/${RUN_ID}-job.json"

if [[ -n "${CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE:-}" ]]; then
  capture_time_vars gemini_started
  cp "${CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE}" "$RAW_OUTPUT_FILE"
  capture_time_vars gemini_finished
else
  if [[ ! -x "$GEMINI_BIN" ]]; then
    write_blocked_result_json \
      "Gemini binary not found: $GEMINI_BIN" \
      "Gemini automation stopped before model execution." \
      "low"
    emit_final_output 1
    exit $?
  fi

  capture_time_vars gemini_started
  if run_gemini_cli "$(cat "$PROMPT_FILE")"; then
    :
  else
    gemini_exit_code="$?"
    capture_time_vars gemini_finished
    cp "$RAW_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-gemini-output.json" 2>/dev/null || true
    if [[ -f "$GEMINI_TIMEOUT_FLAG_FILE" ]]; then
      write_blocked_result_json \
        "Gemini CLI timed out after ${GEMINI_TIMEOUT_SECONDS}s." \
        "Gemini automation stopped because headless execution exceeded the timeout." \
        "low"
    else
      write_blocked_result_json \
        "Gemini CLI exited with status ${gemini_exit_code}." \
        "Gemini automation stopped during headless execution." \
        "low"
    fi
    emit_final_output "$gemini_exit_code"
    exit $?
  fi
  capture_time_vars gemini_finished
fi

cp "$RAW_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-gemini-output.json"

if ! jq . "$RAW_OUTPUT_FILE" >/dev/null 2>&1; then
  write_blocked_result_json \
    "Gemini did not return valid JSON." \
    "Gemini automation stopped because the model response was not parseable JSON." \
    "low"
  emit_final_output 1
  exit $?
fi

if jq -e '.response and (.response | type == "string")' "$RAW_OUTPUT_FILE" >/dev/null 2>&1; then
  jq -r '.response' "$RAW_OUTPUT_FILE" >"$PLAN_OUTPUT_FILE"
else
  cp "$RAW_OUTPUT_FILE" "$PLAN_OUTPUT_FILE"
fi

if ! jq . "$PLAN_OUTPUT_FILE" >/dev/null 2>&1; then
  write_blocked_result_json \
    "Gemini response payload did not contain valid plan JSON." \
    "Gemini automation stopped because the extracted plan payload was not valid JSON." \
    "low"
  emit_final_output 1
  exit $?
fi

cp "$PLAN_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-plan.json"

capture_time_vars exec_started
if run_exec_safe; then
  exec_exit_code=0
else
  exec_exit_code="$?"
fi
capture_time_vars exec_finished

if [[ -f "${RUNS_DIR}/${RUN_ID}-exec-results.json" ]] && jq . "${RUNS_DIR}/${RUN_ID}-exec-results.json" >/dev/null 2>&1; then
  cp "${RUNS_DIR}/${RUN_ID}-exec-results.json" "$BASE_RESULT_FILE"
elif jq . "$EXEC_OUTPUT_FILE" >/dev/null 2>&1; then
  cp "$EXEC_OUTPUT_FILE" "$BASE_RESULT_FILE"
else
  write_blocked_result_json \
    "Executor did not return valid JSON." \
    "Gemini automation stopped during safe command execution." \
    "low"
  exec_exit_code=1
fi

emit_final_output "$exec_exit_code"
exit $?
