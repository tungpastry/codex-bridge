# SOP Tiếng Việt

Tài liệu này biến các workflow chính thành checklist lặp lại được cho operator.

Tài liệu liên quan:

- [Luồng công việc](./workflow-vi.md)
- [Khắc phục sự cố](./troubleshooting-vi.md)
- [Tích hợp MiddayCommander](./targets/middaycommander-vi.md)
- [English version](./sop.md)

## SOP Morning Check

Mục tiêu:

- xác nhận router còn reach được
- xác nhận các node chính còn nhìn thấy nhau
- phát hiện các incident rõ ràng từ sớm

Checklist:

1. Chạy `scripts/mac/codex-bridge-health.sh`.
2. Chạy `scripts/mac/codex-bridge-morning-check.sh`.
3. Xem report được sinh trong `storage/reports/`.
4. Rà các service failed, inactive, hoặc bất thường.
5. Escalate các phát hiện rủi ro sang người thật trước khi thay đổi gì thêm.

## SOP Intake Cho Việc Code

Mục tiêu:

- giữ task code sạch, scoped, và reviewable

Checklist:

1. Gom issue title, repo, và raw context.
2. Chạy `scripts/mac/codex-bridge-dispatch.sh task ...` hoặc `scripts/mac/codex-bridge-make-brief.sh ...`.
3. Nếu route là `codex`, copy brief đã sinh vào Codex App.
4. Giữ implementation bám đúng goal và constraints.
5. Chạy test hoặc smoke check trong target repo.
6. Review patch trước khi commit.

## SOP Incident

Mục tiêu:

- inspect hệ thống một cách an toàn
- tránh ứng biến destructive khi đang áp lực

Checklist:

1. Chạy `scripts/mac/codex-bridge-triage-log.sh <service>` hoặc dispatch mô tả vấn đề.
2. Xem summary và route được khuyến nghị.
3. Nếu an toàn, chạy `scripts/mac/codex-bridge-auto.sh ...` hoặc push Gemini job sang Mac.
4. Review các command đã chạy, final Markdown, và timing output.
5. Dừng ngay nếu route thành `human` hoặc plan bị block.

## SOP Kiểm Tra Sau Deploy

Mục tiêu:

- xác nhận router khỏe sau deploy hoặc upgrade

Checklist:

1. Kiểm tra `systemctl status codex-bridge.service`.
2. Kiểm tra `GET /health`.
3. Kiểm tra `GET /health?depth=full`.
4. Xem migration log entries của run index.
5. Chạy một dispatch smoke test nhỏ nếu behavior vừa đổi.

## SOP Cuối Ngày

Mục tiêu:

- để lại handoff rõ ràng
- giữ lại open risk và next actions

Checklist:

1. Gom các việc đã xong, open issues, và next actions.
2. Chạy `scripts/mac/codex-bridge-daily-report.sh`.
3. Lưu hoặc chia sẻ Markdown report.
4. Ghi lại các mục bị block hoặc rủi ro vẫn cần người thật xử lý.

## SOP Review Artifact

Khi có Gemini automation, hãy xem các file sau trong `storage/gemini_runs/`:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

Dùng chúng để trả lời:

- router đã sinh job gì
- Gemini thực sự trả gì
- command nào đã được chạy
- run có timeout hoặc interrupted không
- thời gian nằm ở model hay execution
