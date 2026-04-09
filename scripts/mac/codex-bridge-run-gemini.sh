#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python3"
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

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
if [[ -z "${CODEX_BRIDGE_BASE_URL:-}" ]]; then
  CODEX_BRIDGE_BASE_URL="$(load_env_value CODEX_BRIDGE_BASE_URL || true)"
fi
if [[ -z "${CODEX_BRIDGE_INTERNAL_API_TOKEN:-}" ]]; then
  CODEX_BRIDGE_INTERNAL_API_TOKEN="$(load_env_value CODEX_BRIDGE_INTERNAL_API_TOKEN || true)"
fi
if [[ -z "${CODEX_BRIDGE_BASE_URL:-}" ]]; then
  CODEX_BRIDGE_BASE_URL="http://192.168.1.15:8787"
fi

load_auth_env_value() {
  local key="$1"
  local value=""

  if [[ -n "${!key:-}" ]]; then
    export "$key"
    return 0
  fi

  value="$(load_env_value "$key" || true)"
  if [[ -n "$value" ]]; then
    printf -v "$key" '%s' "$value"
    export "$key"
  fi
}

load_auth_env_value GEMINI_API_KEY
load_auth_env_value GOOGLE_API_KEY
load_auth_env_value GOOGLE_CLOUD_PROJECT
load_auth_env_value GOOGLE_CLOUD_LOCATION
load_auth_env_value GOOGLE_APPLICATION_CREDENTIALS

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
STDERR_OUTPUT_FILE="${TMP_DIR}/gemini-stderr-output.txt"
PARSED_OUTPUT_FILE="${TMP_DIR}/gemini-parsed-output.json"
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
GEMINI_AUTH_REQUIRED_FLAG_FILE="${TMP_DIR}/gemini-auth-required.flag"

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
    "$PYTHON_BIN" -c 'from datetime import datetime, timezone; now = datetime.now(timezone.utc); print(now.strftime("%Y-%m-%dT%H:%M:%SZ"), int(now.timestamp() * 1000), now.strftime("%Y%m%dT%H%M%SZ"))'
  )

  printf -v "${prefix}_at" '%s' "$captured_at"
  printf -v "${prefix}_ms" '%s' "$captured_ms"
  printf -v "${prefix}_stamp" '%s' "$captured_stamp"
}

format_duration_seconds() {
  "$PYTHON_BIN" -c 'import sys; print(f"{int(sys.argv[1]) / 1000:.1f}s")' "${1:-0}"
}

extract_json_payload() {
  local input_file="$1"
  local output_file="$2"

  "$PYTHON_BIN" - "$input_file" "$output_file" <<'PY'
import json
import sys
from pathlib import Path

input_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
raw_text = input_path.read_text(encoding="utf-8", errors="replace")

def try_write(candidate: str) -> bool:
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return False
    output_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return True

stripped = raw_text.strip()
if stripped and try_write(stripped):
    raise SystemExit(0)

decoder = json.JSONDecoder()
for index, char in enumerate(raw_text):
    if char not in "{[":
        continue
    try:
        obj, _end = decoder.raw_decode(raw_text[index:])
    except json.JSONDecodeError:
        continue
    output_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(1)
PY
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

  if [[ -n "${CODEX_BRIDGE_INTERNAL_API_TOKEN:-}" && -f "$FINAL_OUTPUT_FILE" ]]; then
    "$PYTHON_BIN" -m app.execution.cli post-callback \
      --run-id "$RUN_ID" \
      --payload-file "$FINAL_OUTPUT_FILE" \
      --job-file "${RUNS_DIR}/${RUN_ID}-job.json" \
      --plan-file "${RUNS_DIR}/${RUN_ID}-plan.json" \
      --exec-output-file "${RUNS_DIR}/${RUN_ID}-exec-results.json" \
      --timing-file "$TIMING_FILE" \
      --final-output-file "$FINAL_OUTPUT_FILE" \
      --base-url "${CODEX_BRIDGE_BASE_URL}" \
      --token "${CODEX_BRIDGE_INTERNAL_API_TOKEN}" >/dev/null 2>&1 || true
  fi

  return "$exit_code"
}

run_gemini_cli() {
  local prompt_file="$1"
  local exit_code=0

  rm -f "$GEMINI_TIMEOUT_FLAG_FILE"
  rm -f "$GEMINI_AUTH_REQUIRED_FLAG_FILE"
  ACTIVE_PHASE="gemini_headless"
  "$PYTHON_BIN" - "$GEMINI_BIN" "$prompt_file" "$RAW_OUTPUT_FILE" "$STDERR_OUTPUT_FILE" "$GEMINI_TIMEOUT_FLAG_FILE" "$GEMINI_AUTH_REQUIRED_FLAG_FILE" "$GEMINI_TIMEOUT_SECONDS" <<'PY' &
from __future__ import annotations

import os
import re
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

gemini_bin = sys.argv[1]
prompt_file = Path(sys.argv[2])
stdout_file = Path(sys.argv[3])
stderr_file = Path(sys.argv[4])
timeout_flag_file = Path(sys.argv[5])
auth_flag_file = Path(sys.argv[6])
timeout_seconds = int(sys.argv[7])

prompt_text = prompt_file.read_text(encoding="utf-8")
pattern = re.compile(
    r"Opening authentication page in your browser|How would you like to authenticate|Do you want to continue\? \[Y/n\]:",
    re.IGNORECASE,
)

proc = subprocess.Popen(
    [gemini_bin, "-p", prompt_text, "--output-format", "json"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

selector = selectors.DefaultSelector()
stdout_handle = proc.stdout
stderr_handle = proc.stderr
assert stdout_handle is not None
assert stderr_handle is not None
selector.register(stdout_handle, selectors.EVENT_READ, ("stdout", stdout_file))
selector.register(stderr_handle, selectors.EVENT_READ, ("stderr", stderr_file))

stdout_file.write_bytes(b"")
stderr_file.write_bytes(b"")
recent_chunks: list[str] = []
start = time.monotonic()

def mark_and_stop(flag_path: Path) -> None:
    flag_path.write_text("", encoding="utf-8")
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

while selector.get_map():
    if timeout_seconds > 0 and proc.poll() is None and (time.monotonic() - start) >= timeout_seconds:
        mark_and_stop(timeout_flag_file)

    events = selector.select(timeout=0.2)
    if not events:
        if proc.poll() is not None:
            for key in list(selector.get_map().values()):
                selector.unregister(key.fileobj)
            break
        continue

    for key, _ in events:
        stream_name, output_path = key.data
        chunk = os.read(key.fd, 4096)
        if not chunk:
            selector.unregister(key.fileobj)
            continue

        with output_path.open("ab") as handle:
            handle.write(chunk)

        recent_chunks.append(chunk.decode("utf-8", errors="replace"))
        if len(recent_chunks) > 8:
            recent_chunks.pop(0)

        if proc.poll() is None and pattern.search("".join(recent_chunks)):
            mark_and_stop(auth_flag_file)

return_code = proc.wait()
raise SystemExit(return_code)
PY
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
  jq '. + {interrupted_flag:true, phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
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
RUN_ID="$(jq -r '.run_id // empty' "$JOB_FILE")"
RUN_ID="${RUN_ID:-${JOB_ID:-$RUN_ID}}"
JOB_ID="${JOB_ID:-$RUN_ID}"
TIMING_FILE="${RUNS_DIR}/${RUN_ID}-timing.json"
FINAL_OUTPUT_FILE="${RUNS_DIR}/${RUN_ID}-final.json"

jq -r '.prompt // empty' "$JOB_FILE" >"$PROMPT_FILE"
cp "$JOB_FILE" "${RUNS_DIR}/${RUN_ID}-job.json"

if [[ -n "${CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE:-}" ]]; then
  capture_time_vars gemini_started
  cp "${CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE}" "$RAW_OUTPUT_FILE"
  : >"$STDERR_OUTPUT_FILE"
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
  if run_gemini_cli "$PROMPT_FILE"; then
    :
  else
    gemini_exit_code="$?"
    capture_time_vars gemini_finished
    cp "$RAW_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-gemini-output.json" 2>/dev/null || true
    if [[ -f "$GEMINI_AUTH_REQUIRED_FLAG_FILE" ]]; then
      write_blocked_result_json \
        "Gemini CLI requested interactive browser authentication. Headless mode on this runner requires cached credentials or environment-based authentication such as GEMINI_API_KEY or Vertex AI." \
        "Gemini automation stopped because headless authentication is not configured." \
        "low"
      jq '. + {needs_human:true, phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
    elif [[ -f "$GEMINI_TIMEOUT_FLAG_FILE" ]]; then
      write_blocked_result_json \
        "Gemini CLI timed out after ${GEMINI_TIMEOUT_SECONDS}s." \
        "Gemini automation stopped because headless execution exceeded the timeout." \
        "low"
      jq '. + {timeout_flag:true, phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
    else
      write_blocked_result_json \
        "Gemini CLI exited with status ${gemini_exit_code}." \
        "Gemini automation stopped during headless execution." \
        "low"
      jq '. + {phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
    fi
    emit_final_output "$gemini_exit_code"
    exit $?
  fi
  capture_time_vars gemini_finished
fi

if [[ -f "$GEMINI_AUTH_REQUIRED_FLAG_FILE" ]]; then
  cp "$RAW_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-gemini-output.json" 2>/dev/null || true
  write_blocked_result_json \
    "Gemini CLI requested interactive browser authentication. Headless mode on this runner requires cached credentials or environment-based authentication such as GEMINI_API_KEY or Vertex AI." \
    "Gemini automation stopped because headless authentication is not configured." \
    "low"
  jq '. + {needs_human:true, phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
  emit_final_output 1
  exit $?
fi

if extract_json_payload "$RAW_OUTPUT_FILE" "$PARSED_OUTPUT_FILE"; then
  cp "$PARSED_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-gemini-output.json"
else
  cp "$RAW_OUTPUT_FILE" "${RUNS_DIR}/${RUN_ID}-gemini-output.json"
fi

if ! [[ -s "$PARSED_OUTPUT_FILE" ]] || ! jq . "$PARSED_OUTPUT_FILE" >/dev/null 2>&1; then
  write_blocked_result_json \
    "Gemini did not return valid JSON." \
    "Gemini automation stopped because the model response was not parseable JSON." \
    "low"
  jq '. + {phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
  emit_final_output 1
  exit $?
fi

if jq -e '.response and (.response | type == "string")' "$PARSED_OUTPUT_FILE" >/dev/null 2>&1; then
  jq -r '.response' "$PARSED_OUTPUT_FILE" >"$PLAN_OUTPUT_FILE"
else
  cp "$PARSED_OUTPUT_FILE" "$PLAN_OUTPUT_FILE"
fi

if ! jq . "$PLAN_OUTPUT_FILE" >/dev/null 2>&1; then
  write_blocked_result_json \
    "Gemini response payload did not contain valid plan JSON." \
    "Gemini automation stopped because the extracted plan payload was not valid JSON." \
    "low"
  jq '. + {phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
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
  jq '. + {phase:"final"}' "$BASE_RESULT_FILE" >"${BASE_RESULT_FILE}.tmp" && mv "${BASE_RESULT_FILE}.tmp" "$BASE_RESULT_FILE"
  exec_exit_code=1
fi

emit_final_output "$exec_exit_code"
exit $?
