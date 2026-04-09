# Hướng Dẫn: Incident Ops Với Gemini Auto Runner

Tài liệu này minh họa một incident low-risk nơi router chọn nhánh Gemini.

Tài liệu liên quan:

- [Luồng công việc](../workflow-vi.md)
- [Khắc phục sự cố](../troubleshooting-vi.md)
- [English version](./ops-incident.md)

## Mục tiêu

Inspect một service theo cách an toàn, để Gemini đề xuất typed commands, và giữ audit trail rõ ràng.

## Tình huống ví dụ

Bạn muốn inspect một service trên `UbuntuDesktop` hoặc `UbuntuServer` mà không nhảy thẳng vào shell ad hoc.

## Bước 1: Triage log

```bash
./scripts/mac/codex-bridge-triage-log.sh cron.service
```

Hãy xem:

- `symptom`
- `likely_cause`
- `recommended_tool`
- `next_step`

## Bước 2: Để dispatch chọn route

```bash
./scripts/mac/codex-bridge-dispatch.sh \
  task \
  "Inspect service health" \
  codex-bridge \
  /path/to/context.txt
```

Nếu route là `gemini`, Mac runner sẽ:

1. nhận `gemini_job`
2. gọi Gemini CLI headless
3. trích JSON plan
4. validate command IDs và hosts
5. thực thi safe commands
6. in final JSON kèm timing data

## Bước 3: Review artifacts

Xem trong `storage/gemini_runs/`:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

## Bước 4: Đọc timing output

Hãy tập trung vào:

- `timing_summary`
- `timing.gemini_cli_duration_ms`
- `timing.exec_duration_ms`
- `timing.total_duration_ms`

## Bước 5: Dừng nếu route chuyển thành human

Nếu router hoặc runner block task:

- không bypass safe command layer
- không chèn shell destructive tùy tiện
- xem `block_reason` và escalate thủ công
