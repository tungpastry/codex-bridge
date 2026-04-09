# Luồng Công Việc

Tài liệu này mô tả các workflow generic mà `codex-bridge` hỗ trợ.

Tài liệu liên quan:

- [README](../README.md)
- [Kiến trúc](./architecture-vi.md)
- [Triển khai](./deployment-vi.md)
- [SOP tiếng Việt](./sop-vi.md)
- [Tích hợp MiddayCommander](./targets/middaycommander-vi.md)
- [English version](./workflow.md)

## 1. Việc Code sang Codex

Các trường hợp thường gặp:

- làm feature
- sửa bug
- code review có khả năng dẫn đến patch
- setup nhưng vẫn phải sửa code

Luồng khuyến nghị:

1. gom task title, repo name, và raw context
2. gọi `scripts/mac/codex-bridge-dispatch.sh task ...` hoặc `scripts/mac/codex-bridge-make-brief.sh ...`
3. nếu route là `codex`, xem `codex_brief_markdown`
4. paste brief vào Codex App theo cách thủ công
5. implement và validate patch trong repo mục tiêu

Vì sao route này tồn tại:

- task code cần context sạch và có cấu trúc
- implementation và review vẫn cần con người kiểm soát
- `codex-bridge` giúp route và làm sạch context, chứ không giả định code change là an toàn để tự chạy

Điểm dừng:

- nếu task trở thành việc production-risk thì route sang `human`
- nếu task thực ra là điều tra ops thì route sang `gemini`

## 2. Điều Tra Ops An Toàn với Gemini

Các trường hợp thường gặp:

- kiểm tra health của service
- xem log low-risk
- kiểm tra port, disk, memory, uptime
- restart service nằm trong allowlist nếu plan vẫn an toàn

Luồng khuyến nghị:

1. tóm tắt vấn đề bằng `scripts/mac/codex-bridge-triage-log.sh` hoặc `dispatch`
2. xác nhận route là `gemini`
3. để Mac runner gọi Gemini CLI headless
4. validate typed plan mà Gemini trả về
5. chỉ thực thi các command được phép
6. xem `final_markdown`, timing, và artifacts đã lưu

Route này phù hợp với:

- service inspection gần đây
- operator workflow low-risk
- nhu cầu quan sát rõ bằng run artifacts và run index

Điểm dừng:

- route chuyển thành `human`
- plan tham chiếu host hoặc command bị cấm
- issue liên quan auth, firewall, schema, secrets, hoặc destructive operation

## 3. Daily Ops và Reporting

Các trường hợp thường gặp:

- morning check
- operator report ngắn
- handoff summary
- theo dõi tình trạng service lặp lại

Luồng khuyến nghị:

1. chạy `scripts/mac/codex-bridge-health.sh`
2. chạy `scripts/mac/codex-bridge-morning-check.sh`
3. gom các mục đã xong, open issues, và next actions
4. chạy `scripts/mac/codex-bridge-daily-report.sh`

Kết quả mong đợi:

- health summary ngắn
- Markdown dễ đọc cho operator
- runs và artifacts có thể query lại nếu dispatch hoặc Gemini automation được dùng

## 4. Generic Target Integration Workflow

`codex-bridge` được thiết kế để hỗ trợ nhiều target repo mà không kéo target đó thành phần trung tâm của docs lõi.

Mô hình tích hợp chung:

1. định nghĩa profile với repo hints và preferred command hosts nếu cần
2. giữ application code trong repo mục tiêu
3. giữ internal routing, health wrappers, và ops automation trong `codex-bridge`
4. tài liệu target-specific nằm trong `docs/targets/`

Ví dụ cụ thể có thể xem ở [Tích hợp MiddayCommander](./targets/middaycommander-vi.md).

## Ghi Chú Chung

Những nguyên tắc này đúng ở mọi workflow:

- route được chọn một cách tường minh
- việc rủi ro sẽ bị block thay vì “làm thử”
- Codex App luôn giữ manual
- Gemini chỉ được dùng trong safe command boundary có kiểu rõ ràng
- run artifacts và SQLite run index giúp execution observable
- router vẫn heuristic-first chứ không model-first
