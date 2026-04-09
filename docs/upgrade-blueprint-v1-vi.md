# Nâng Cấp Blueprint v1

Tài liệu này tổng kết những gì phần nâng cấp production đã thực sự thay đổi trong hệ thống hiện đang chạy. Đây là tài liệu kiến trúc sau triển khai, không còn là plan tương lai.

Tài liệu liên quan:

- [Kiến trúc](./architecture-vi.md)
- [API Reference tiếng Việt](./api-reference-vi.md)
- [Triển khai](./deployment-vi.md)
- [English version](./upgrade-blueprint-v1.md)

## Mục Tiêu Đã Hoàn Thành

Nâng cấp v1 đã đưa `codex-bridge` từ một router prototype thành một internal platform production-ready hơn, nhưng vẫn giữ nguyên triết lý ban đầu:

- heuristic-first routing
- fail-closed safety
- không điều khiển UI của Codex App
- không cho Gemini chạy shell tùy ý
- run có artifact và có observability rõ

## Các Thay Đổi Lớn Đã Có

### 1. Production Package Structure

App hiện được chia thành các package rõ ràng cho API routes, policy, builders, execution, artifacts, profiles, runtime bootstrap, và run index management.

### 2. SQLite Run Index

Router hiện sở hữu một SQLite run index với migration và query APIs. Nhờ vậy có:

- run summaries được persist
- lịch sử command và rule
- artifact indexing
- admin metrics

### 3. Decision Trace

Các quyết định heuristic hiện được giải thích qua `decision_trace` trong response của classify, log, diff, và dispatch.

### 4. Dispatch Persistence

`dispatch` hiện tạo `run_id`, lưu request và response snapshots, index các rules, và theo dõi generated artifacts.

### 5. Typed Execution Model

Gemini plan hiện bị ràng buộc vào typed command specifications thay vì free-form shell instructions.

### 6. Internal Execution Callback

Mac runner cập nhật router-side run index qua callback nội bộ có auth, để execution results luôn observable từ router host.

### 7. Runs Và Metrics APIs

Hệ thống hiện có:

- `/v1/runs`
- `/v1/runs/{run_id}`
- `/v1/runs/{run_id}/artifacts`
- `/v1/admin/metrics`
- `/health?depth=full`

### 8. Profiles Và Preferred Hosts

Profiles YAML hiện cung cấp repo-specific hints ở mức tối giản. Chúng có thể gợi ý likely files, prompt hints, default safe services, và preferred command hosts.

## Những Nguyên Tắc Vẫn Được Giữ Nguyên

Nâng cấp này không thay đổi các ranh giới cốt lõi:

- Codex App vẫn là luồng manual cho việc code
- Gemini vẫn bị giới hạn trong safe command boundary
- việc rủi ro vẫn bị đẩy sang `human`
- hệ thống vẫn cố tình lightweight và local-first

## Ghi Chú Vận Hành

- startup hiện log rõ migration details cho run index
- artifact trên disk vẫn là audit trail đầy đủ
- SQLite là lớp query, không thay thế artifact filesystem
- timing telemetry giúp tách model latency khỏi execution latency

## Những Giới Hạn Vẫn Còn

- chưa có queue hoặc worker fleet
- chưa có distributed job orchestration
- không có browser automation
- không có AppleScript
- không cố tự xử lý các intent mơ hồ hoặc rủi ro trong production
