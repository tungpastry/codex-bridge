# API Reference

This document describes the public FastAPI endpoints exposed by `codex-bridge`.

Base URL examples:

- local Mac development: `http://127.0.0.1:8787`
- UbuntuDesktop on LAN: `http://192.168.1.15:8787`

## GET /health

Purpose:

- confirm the service is reachable
- expose the configured product identity and model settings

Example response:

```json
{
  "status": "ok",
  "service": "codex-bridge",
  "llm_backend": "ollama",
  "model": "gemma3:1b-it-qat",
  "time": "2026-04-08T06:19:11Z"
}
```

## POST /v1/classify/task

Purpose:

- classify a task from raw title and context
- choose `local`, `gemini`, `codex`, or `human`

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | short task title |
| `context` | string | yes | raw context in Vietnamese or English |
| `repo` | string | no | repo name, often `MiddayCommander` |
| `source` | string | no | default `manual` |
| `constraints` | string[] | no | implementation or operator constraints |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `task_type` | string | `bugfix`, `ops`, `setup`, `review`, `deploy`, `research`, `feature`, or `unknown` |
| `severity` | string | `low`, `medium`, `high`, or `critical` |
| `repo` | string | echoed repo |
| `problem_summary` | string | short summary |
| `signals` | string[] | detected task signals |
| `suspected_files` | string[] | file-like hints extracted from context |
| `recommended_tool` | string | `local`, `gemini`, `codex`, or `human` |
| `next_step` | string | practical next action |

## POST /v1/summarize/log

Purpose:

- summarize a log excerpt into a short operator triage packet

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `service` | string | no | service name |
| `log_text` | string | yes | raw log block |
| `repo` | string | no | related repo |
| `context` | string | no | extra operator notes |
| `source` | string | no | default `manual` |
| `host` | string | no | optional host label |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `symptom` | string | short symptom summary |
| `likely_cause` | string | likely cause |
| `important_lines` | string[] | high-signal log lines |
| `recommended_commands` | string[] | suggested inspection commands |
| `needs_codex` | boolean | true if the issue likely needs code changes |
| `recommended_tool` | string | `local`, `gemini`, `codex`, or `human` |
| `next_step` | string | practical next action |

## POST /v1/summarize/diff

Purpose:

- summarize a diff and assess lightweight risk

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `repo` | string | yes | repo name |
| `diff_text` | string | yes | diff contents |
| `base_ref` | string | no | default `main` |
| `head_ref` | string | no | default `HEAD` |
| `context` | string | no | optional notes |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `summary` | string | diff summary |
| `risk_level` | string | `low`, `medium`, or `high` |
| `risk_flags` | string[] | config, auth, database, migration, security hints |
| `review_focus` | string[] | key review bullets |
| `recommended_tool` | string | `local`, `gemini`, `codex`, or `human` |
| `next_step` | string | practical next action |

## POST /v1/compress/context

Purpose:

- compress raw task context into a paste-friendly implementation brief

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | task title |
| `context` | string | yes | raw input text |
| `repo` | string | no | repo name |
| `constraints` | string[] | no | constraints to preserve |
| `target_tool` | string | no | optional hint |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `compressed_context` | string | short implementation brief |
| `key_points` | string[] | extracted high-signal points |
| `constraints` | string[] | preserved constraints |

## POST /v1/brief/codex

Purpose:

- produce a Markdown brief for manual paste into Codex App

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | task title |
| `repo` | string | yes | target repo |
| `context` | string | yes | cleaned task context |
| `constraints` | string[] | no | constraints |
| `acceptance_criteria` | string[] | no | acceptance criteria |
| `likely_files` | string[] | no | likely touched files |
| `notes` | string[] | no | extra notes |
| `task_type` | string | no | optional override |
| `goal` | string | no | optional goal |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `brief_markdown` | string | final Markdown brief |
| `task_type` | string | inferred or provided task type |
| `recommended_tool` | string | always `codex` |

## POST /v1/report/daily

Purpose:

- turn free-form progress notes into a short daily report

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `repo` | string | no | optional repo |
| `items` | string[] | no | list of pre-split notes |
| `raw_text` | string | no | free-form text |
| `context` | string | no | extra notes |
| `source` | string | no | default `manual` |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `markdown` | string | final Markdown report |
| `done` | string[] | completed items |
| `open_issues` | string[] | unresolved issues |
| `next_actions` | string[] | next actions |

## POST /v1/dispatch/task

Purpose:

- combine classification, route selection, and artifact building into one canonical response

Request fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | task title |
| `input_kind` | string | yes | `task`, `log`, `diff`, or `report` |
| `context` | string | yes | raw input |
| `repo` | string | no | repo name |
| `source` | string | no | default `manual` |
| `constraints` | string[] | no | route constraints |
| `target_host` | string | no | service or host hint, commonly used with logs |

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `route` | string | `codex`, `gemini`, `human`, or `local` |
| `task_type` | string | inferred route type |
| `severity` | string | `low`, `medium`, `high`, or `critical` |
| `problem_summary` | string | short summary |
| `next_step` | string | practical next action |
| `codex_brief_markdown` | string or null | present for `codex` route |
| `gemini_job` | object or null | present for `gemini` route |
| `human_summary` | string or null | present for `human` route |
| `block_reason` | string or null | present for `human` route |
| `local_summary` | string or null | present for `local` route |

### Gemini Job Shape

When `route=gemini`, the response includes a `gemini_job` with:

| Field | Type | Notes |
| --- | --- | --- |
| `mode` | string | always `ops_auto` |
| `job_id` | string | stable job identity used by the runner |
| `title` | string | task title |
| `repo` | string | repo name |
| `problem_summary` | string | short summary |
| `context_digest` | string | cleaned context for Gemini |
| `constraints` | string[] | preserved constraints |
| `allowed_hosts` | string[] | `local`, `UbuntuDesktop`, `UbuntuServer` |
| `allowed_command_ids` | string[] | command whitelist |
| `output_contract` | object | required Gemini JSON contract |
| `prompt` | string | rendered prompt text |

## Persistence Behavior

Each endpoint saves request and response snapshots under `storage/requests/` and `storage/responses/`.

Extra persistence:

- `/v1/brief/codex` saves Markdown into `storage/reports/`
- `/v1/report/daily` saves Markdown into `storage/reports/`
- Gemini auto-runs save artifacts under `storage/gemini_runs/`
