# API Reference

Tai lieu nay mo ta cac endpoint quan trong cua `codex-bridge` sau khi nang cap theo Production Upgrade Blueprint v1.

Base URL thuong gap:

- local Mac: `http://127.0.0.1:8787`
- router tren UbuntuDesktop: `http://192.168.1.15:8787`

## GET /health

Health check co ban, giu backward-compatible.

Example:

```json
{
  "status": "ok",
  "service": "codex-bridge",
  "llm_backend": "ollama",
  "model": "gemma3:1b-it-qat",
  "time": "2026-04-09T01:00:00Z"
}
```

## GET /health?depth=full

Tra them thong tin local diagnostics cua router:

- thong tin run index
- migration version hien tai
- storage root
- profile da load
- allowed hosts va so command duoc phep

Example:

```json
{
  "status": "ok",
  "service": "codex-bridge",
  "llm_backend": "ollama",
  "model": "gemma3:1b-it-qat",
  "time": "2026-04-09T01:00:00Z",
  "depth": "full",
  "index": {
    "status": "ok",
    "db_path": "/home/nexus/codex-bridge/storage/index/runs.db",
    "user_version": 2
  },
  "storage_dir": "/home/nexus/codex-bridge/storage",
  "profiles": {
    "count": 2,
    "names": ["MiddayCommander", "codex-bridge"]
  },
  "execution": {
    "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
    "allowed_command_count": 15
  }
}
```

## POST /v1/classify/task

Phan loai task dua tren heuristic va tra them `decision_trace`.

Request:

```json
{
  "title": "MiddayCommander loi build",
  "context": "Go test that bai voi panic trong transfer queue.",
  "repo": "MiddayCommander",
  "source": "manual",
  "constraints": ["Patch nho"]
}
```

Response fields:

- `task_type`
- `severity`
- `repo`
- `problem_summary`
- `signals`
- `suspected_files`
- `recommended_tool`
- `next_step`
- `decision_trace`

## POST /v1/summarize/log

Tom tat log, tra ve symptom, likely cause, recommended commands, va `decision_trace`.

Response fields:

- `symptom`
- `likely_cause`
- `important_lines`
- `recommended_commands`
- `needs_codex`
- `recommended_tool`
- `next_step`
- `decision_trace`

## POST /v1/summarize/diff

Tom tat diff va danh gia risk level.

Response fields:

- `summary`
- `risk_level`
- `risk_flags`
- `review_focus`
- `recommended_tool`
- `next_step`
- `decision_trace`

## POST /v1/compress/context

Nen context thanh brief ngan gon de paste.

Response fields:

- `compressed_context`
- `key_points`
- `constraints`

## POST /v1/brief/codex

Sinh Markdown brief de paste thu cong vao Codex App.

Response fields:

- `brief_markdown`
- `task_type`
- `recommended_tool`

## POST /v1/report/daily

Chuyen ghi chu thanh bao cao ngan.

Response fields:

- `markdown`
- `done`
- `open_issues`
- `next_actions`

## POST /v1/dispatch/task

Day la endpoint orchestration chinh.

No:

- phan loai task
- tao `run_id`
- luu request/response snapshots
- persist matched rules vao run index
- tao artifact phu hop cho route duoc chon

Request:

```json
{
  "title": "Inspect codex-bridge health",
  "input_kind": "task",
  "context": "Check service status and router health only with safe commands",
  "repo": "codex-bridge",
  "source": "manual",
  "constraints": ["Safe commands only"]
}
```

Response fields:

- `run_id`
- `route`
- `task_type`
- `severity`
- `problem_summary`
- `next_step`
- `codex_brief_markdown`
- `gemini_job`
- `human_summary`
- `block_reason`
- `local_summary`
- `decision_trace`
- `artifacts`

`artifacts.generated` chi tra metadata, khong tra noi dung file.

Artifact taxonomy da chot trong v1:

- `request_snapshot`
- `response_snapshot`
- `codex_brief`
- `daily_report`
- `gemini_job`
- `execution_plan`
- `execution_result`
- `timing`
- `final_result`

## GET /v1/runs

Liet ke run da persist trong SQLite index.

Query params:

- `repo`
- `route`
- `status`
- `date` theo UTC dang `YYYY-MM-DD`
- `limit`
- `offset`

Sort mac dinh:

- `created_at DESC`

Response:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Moi item la run summary co cac field high-signal nhu:

- `run_id`
- `created_at`
- `finished_at`
- `status`
- `route`
- `input_kind`
- `repo`
- `profile_name`
- `title`
- `task_type`
- `severity`
- `blocked_flag`
- `timeout_flag`
- `interrupted_flag`
- `needs_human_flag`
- `timing_total_ms`
- `command_count`

## GET /v1/runs/{run_id}

Tra chi tiet mot run:

- `run`
- `rules`
- `commands`
- `artifacts`

`commands` da duoc normalize theo typed execution model:

- `host`
- `command_id`
- `status`
- `exit_code`
- `duration_ms`
- `stdout_excerpt`
- `stderr_excerpt`
- `truncated_flag`

## GET /v1/runs/{run_id}/artifacts

Tra danh sach artifact metadata cua mot run.

Response:

```json
{
  "run_id": "run-123",
  "items": []
}
```

## GET /v1/admin/metrics

Tra metric tong hop tu SQLite run index.

Response:

```json
{
  "runs_total": 12,
  "runs_today": 4,
  "blocked_today": 1,
  "timeouts_today": 0,
  "route_distribution": {
    "codex": 3,
    "gemini": 6,
    "human": 2,
    "local": 1
  },
  "average_timing_ms": {
    "total": 1840,
    "model": 1030,
    "exec": 520
  }
}
```

## POST /v1/internal/runs/{run_id}/execution

Day la callback noi bo de Mac Gemini runner cap nhat lai run index tren router.

Yeu cau:

- header `X-Codex-Bridge-Token`
- body phai co `phase`
- duoc thiet ke idempotent theo `run_id + phase`

Callback co the cap nhat:

- `status`
- `timeout_flag`
- `interrupted_flag`
- `needs_human`
- `timing`
- `results`
- `artifacts`

Endpoint nay khong danh cho client cong khai.
