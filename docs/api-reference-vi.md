# API Reference Tiếng Việt

Tài liệu này mô tả các API public và internal hiện tại của `codex-bridge`.

Tài liệu liên quan:

- [README](../README.md)
- [Kiến trúc](./architecture-vi.md)
- [Triển khai](./deployment-vi.md)
- [Khắc phục sự cố](./troubleshooting-vi.md)
- [English version](./api-reference.md)

Base URL thường gặp:

- local development: `http://127.0.0.1:8787`
- router trên UbuntuDesktop: `http://192.168.1.15:8787`

## Quy ước chung

- Tất cả timestamp dùng UTC ISO string.
- `/v1/runs` mặc định sort theo `created_at DESC`.
- Artifact của dispatch và execution vừa được lưu trên disk, vừa được index trong SQLite.
- Các response heuristic hiện có thêm `decision_trace`.

## GET /health

Health check cơ bản, giữ backward-compatible.

Ví dụ:

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

Trả thêm thông tin local diagnostics của router.

Các field bổ sung:

- `depth`
- `index.status`
- `index.db_path`
- `index.user_version`
- `storage_dir`
- `profiles.count`
- `profiles.names`
- `execution.allowed_hosts`
- `execution.allowed_command_count`

## POST /v1/classify/task

Phân loại task bằng heuristic và đề xuất route tiếp theo.

Request:

- `title`
- `context`
- `repo`
- `source`
- `constraints[]`

Response:

- `task_type`
- `severity`
- `repo`
- `problem_summary`
- `signals[]`
- `suspected_files[]`
- `recommended_tool`
- `next_step`
- `decision_trace`

## POST /v1/summarize/log

Tóm tắt log và gợi ý workflow an toàn tiếp theo.

Request:

- `service`
- `log_text`
- `repo`
- `context`
- `source`
- `host`

Response:

- `symptom`
- `likely_cause`
- `important_lines[]`
- `recommended_commands[]`
- `needs_codex`
- `recommended_tool`
- `next_step`
- `decision_trace`

## POST /v1/summarize/diff

Tóm tắt diff và đưa ra góc nhìn review theo risk.

Request:

- `repo`
- `diff_text`
- `base_ref`
- `head_ref`
- `context`

Response:

- `summary`
- `risk_level`
- `risk_flags[]`
- `review_focus[]`
- `recommended_tool`
- `next_step`
- `decision_trace`

## POST /v1/compress/context

Nén raw context thành bản ngắn gọn, dễ paste.

Response:

- `compressed_context`
- `key_points[]`
- `constraints[]`

## POST /v1/brief/codex

Sinh Markdown brief để paste thủ công vào Codex App.

Request có thể gồm:

- `title`
- `repo`
- `context`
- `constraints[]`
- `acceptance_criteria[]`
- `likely_files[]`
- `notes[]`
- `task_type`
- `goal`

Response:

- `brief_markdown`
- `task_type`
- `recommended_tool`

## POST /v1/report/daily

Sinh báo cáo Markdown ngắn.

Request:

- `repo`
- `items[]`
- `raw_text`
- `context`
- `source`

Response:

- `markdown`
- `done[]`
- `open_issues[]`
- `next_actions[]`

## POST /v1/dispatch/task

Đây là endpoint orchestration chính.

Nó sẽ:

- phân loại input
- tạo `run_id`
- lưu request và response snapshots
- persist matched rules vào run index
- tạo artifact phù hợp với route
- trả payload của route đã chọn

Request:

- `title`
- `input_kind`
- `context`
- `repo`
- `source`
- `constraints[]`
- `target_host`

Response:

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

Các route outcomes:

- `codex`
- `gemini`
- `human`
- `local`

### Gemini job fields

Khi route là `gemini`, `gemini_job` có thể gồm:

- `run_id`
- `job_id`
- `title`
- `repo`
- `profile_name`
- `problem_summary`
- `context_digest`
- `constraints[]`
- `allowed_hosts[]`
- `allowed_command_ids[]`
- `preferred_command_hosts`
- `output_contract`
- `prompt`

`preferred_command_hosts` dùng để gợi Gemini chọn đúng host cho từng `command_id`, nhưng vẫn không cho phép host selection tùy tiện.

### Dispatch artifacts block

`artifacts` chỉ trả metadata, không trả nội dung file:

- `request_snapshot_path`
- `response_snapshot_path`
- `generated[]`

Taxonomy artifact hiện tại:

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

Liệt kê các run đã được persist trong SQLite index.

Query params:

- `repo`
- `route`
- `status`
- `date` theo UTC dạng `YYYY-MM-DD`
- `limit` mặc định `50`, tối đa `200`
- `offset`

Sort mặc định:

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

Mỗi run summary gồm các field quan trọng như:

- `run_id`
- `job_id`
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
- `timing_model_ms`
- `timing_exec_ms`
- `command_count`

## GET /v1/runs/{run_id}

Trả đầy đủ góc nhìn indexed của một run.

Response:

- `run`
- `rules`
- `commands`
- `artifacts`

`commands` là normalized execution results và có thể gồm:

- `ordinal`
- `host`
- `command_id`
- `reason`
- `shell_command`
- `status`
- `exit_code`
- `started_at`
- `finished_at`
- `duration_ms`
- `stdout_excerpt`
- `stderr_excerpt`
- `truncated_flag`
- `output_path`

## GET /v1/runs/{run_id}/artifacts

Trả artifact index entries của một run.

Response:

- `run_id`
- `items[]`

## GET /v1/admin/metrics

Trả metrics tổng hợp từ run index.

Response:

- `runs_total`
- `runs_today`
- `blocked_today`
- `timeouts_today`
- `route_distribution`
- `average_timing_ms.total`
- `average_timing_ms.model`
- `average_timing_ms.exec`

## POST /v1/internal/runs/{run_id}/execution

Đây là callback nội bộ để Mac runner cập nhật router-side run index.

Yêu cầu:

- header `X-Codex-Bridge-Token`
- JSON payload có kiểu rõ ràng
- `phase`

Payload có thể gồm:

- `phase`
- `status`
- `summary`
- `confidence`
- `why`
- `final_markdown`
- `block_reason`
- `needs_human`
- `timeout_flag`
- `interrupted_flag`
- `timing`
- `results[]`
- `artifacts[]`

`results[]` là normalized execution records, không phải free-form shell transcript.

## Cam kết của execution boundary

Contract execution hiện tại giữ các ranh giới sau:

- Gemini không được gửi arbitrary shell để thực thi.
- Command phải đi qua `command_id + args`.
- Allowed hosts chỉ là `local`, `UbuntuDesktop`, `UbuntuServer`.
- Restart chỉ được phép với service nằm trong allowlist.
- Command bị cấm hoặc mơ hồ phải fail-closed thay vì thực thi.
