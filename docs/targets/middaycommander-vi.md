# Tích Hợp MiddayCommander

Tài liệu này mô tả cách `MiddayCommander` sử dụng `codex-bridge` mà không kéo target repo trở thành trung tâm của docs kiến trúc lõi.

Tài liệu liên quan:

- [README](../../README.md)
- [Luồng công việc](../workflow-vi.md)
- [SOP tiếng Việt](../sop-vi.md)
- [English version](./middaycommander.md)

## Vì Sao MiddayCommander Dùng Codex Bridge

`MiddayCommander` dùng `codex-bridge` cho:

- deploy wrappers của router
- health checks trên mô hình đa node
- morning check cho operator
- release preparation và promotion helpers
- lớp internal automation không nên đặt trong product repo

Application code vẫn nằm trong repo `MiddayCommander`. `codex-bridge` chỉ giữ lớp routing và operator tooling xung quanh nó.

## Các Script Liên Quan

Các script target-specific hiện có:

- `scripts/mac/middaycommander-deploy-router.sh`
- `scripts/mac/middaycommander-health.sh`
- `scripts/mac/middaycommander-morning-check.sh`
- `scripts/mac/middaycommander-release.sh`

## Deploy Wrapper

`middaycommander-deploy-router.sh` dùng để refresh router deployment trên `UbuntuDesktop`.

Trách nhiệm thường gặp:

- sync source tree của `codex-bridge`
- tránh sync hidden macOS sidecar files
- refresh Python environment ở remote khi cần
- để lại bước restart hoặc post-deploy verification rõ ràng cho operator

## Health Wrapper

`middaycommander-health.sh` cung cấp health view có hiểu biết target trên cả ba node.

Nó hữu ích cho:

- router visibility
- runtime node visibility
- target repo state
- release visibility trên UbuntuServer

## Morning Check Wrapper

`middaycommander-morning-check.sh` tạo Markdown handoff report có timestamp dành riêng cho môi trường MiddayCommander.

Dùng khi:

- bạn muốn morning health report lặp lại được
- bạn cần handoff artifact ngắn cho operator
- bạn muốn trạng thái target-specific nằm cùng một chỗ

## Release Flow

`middaycommander-release.sh` là helper release dành riêng cho target này. Nó hỗ trợ:

- dry-run validation
- build preparation
- publish GitHub release
- promote Linux artifact sang managed release directory

Đây là flow target-specific, nên cố tình không nằm trong workflow docs lõi của `codex-bridge`.

## Ghi Chú Vận Hành

- giữ logic target-specific trong `docs/targets/` và target wrappers, không trộn vào docs kiến trúc lõi
- giữ code ứng dụng và business logic trong target repo
- chỉ dùng profiles và prompt hints của `codex-bridge` để cải thiện routing và safe automation, không dùng để nới lỏng safety rules
