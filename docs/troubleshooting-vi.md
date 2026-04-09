# Khắc Phục Sự Cố

Tài liệu này gom lại các lỗi quan trọng nhất đã gặp trong quá trình bring-up và upgrade của `codex-bridge`.

Tài liệu liên quan:

- [Triển khai](./deployment-vi.md)
- [Kiến trúc](./architecture-vi.md)
- [API Reference tiếng Việt](./api-reference-vi.md)
- [English version](./troubleshooting.md)

## Router Không Khởi Động Được

### Triệu chứng

- `systemd` báo service start rồi chết
- local `curl http://127.0.0.1:8787/health` trả connection refused

### Nguyên nhân thường gặp

- `.env` sai
- profile file không đọc được
- thiếu dependency
- runtime path không đúng

### Cách xử lý

- xem `journalctl -u codex-bridge.service -n 120 --no-pager`
- xác nhận `PROMPTS_DIR`, `STORAGE_DIR`, `RUN_INDEX_DB_PATH`, `PROFILES_DIR`
- kiểm tra startup migration logs có xuất hiện hay không

## Hidden AppleDouble Profile Files Làm Loader Hỏng

### Triệu chứng

- service chết sau khi sync file từ macOS sang Linux
- profile loader báo decode error

### Nguyên nhân thường gặp

- các file `._*.yaml` hoặc `.DS_Store` bị copy vào `app/profiles/`

### Cách xử lý

- xóa hidden sidecar files kiểu macOS khỏi `app/profiles/`
- giữ rule deploy không sync `._*` và `.DS_Store`
- dùng loader mới đã bỏ qua hidden files

## Health Chạy Local Được Nhưng Không Gọi Qua LAN Được

### Triệu chứng

- `curl http://127.0.0.1:8787/health` chạy được trên router
- `curl http://192.168.1.15:8787/health` fail khi gọi từ Mac

### Nguyên nhân thường gặp

- firewall hoặc vấn đề LAN reachability

### Cách xử lý

- xác nhận app đang nghe trên `0.0.0.0:8787`
- kiểm tra UFW hoặc firewall khác
- xác nhận IP của router không đổi

## `ssh MacMiniGemini` Báo `Connection refused`

### Triệu chứng

- router push path sang Mac fail ngay

### Nguyên nhân thường gặp

- Remote Login trên Mac chưa bật
- SSH alias hoặc SSH key chưa xong

### Cách xử lý

- bật Remote Login trên Mac
- xác nhận `~/.ssh/config` có `MacMiniGemini`
- test `ssh MacMiniGemini 'hostname && whoami'`

## Gemini Runner Báo `node: No such file or directory`

### Triệu chứng

- Gemini CLI chạy được trong terminal interactive
- nhưng fail khi chạy qua SSH hoặc script

### Nguyên nhân thường gặp

- shell non-interactive không nạp `PATH` của Homebrew

### Cách xử lý

- bootstrap Homebrew shell environment ngay trong runner
- xác nhận script tìm thấy cả `gemini` lẫn `node`

## Gemini CLI Đòi Browser Authentication

### Triệu chứng

- runner block rất nhanh với trạng thái liên quan auth
- Gemini CLI in ra prompt yêu cầu browser auth

### Nguyên nhân thường gặp

- headless auth chưa được cấu hình

### Cách xử lý

- cung cấp cached credentials hoặc env-based auth
- xác nhận runner có thể export các biến auth từ `.env`

## Gemini Trả Rỗng Hoặc Non-JSON

### Triệu chứng

- run bị block trước khi sang bước safe execution
- `final_markdown` báo Gemini không trả JSON hợp lệ

### Nguyên nhân thường gặp

- output của Gemini có banner text hoặc các dòng không phải JSON
- model output malformed

### Cách xử lý

- xem `<run_id>-gemini-output.json`
- xác nhận runner đang dùng JSON extraction path có thể chịu được banner text
- kiểm tra prompt vẫn ép Gemini trả JSON only

## Internal Callback Không Cập Nhật Run Index

### Triệu chứng

- Mac runner in ra final result
- nhưng `/v1/runs/{run_id}` vẫn ở trạng thái `awaiting_execution`

### Nguyên nhân thường gặp

- `CODEX_BRIDGE_BASE_URL` thiếu hoặc sai trên Mac
- `CODEX_BRIDGE_INTERNAL_API_TOKEN` không trùng với router

### Cách xử lý

- xác nhận `CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787`
- xác nhận token giống hệt trên cả hai máy
- chạy lại run và xem log phía router

## `systemctl` Hoặc `journalctl` Chạy Nhầm Host

### Triệu chứng

- run đi tới execution
- nhưng command service lại chạy trên node không đúng

### Nguyên nhân thường gặp

- profile chưa có `preferred_command_hosts`
- router đang chạy prompt hoặc profile cũ

### Cách xử lý

- xác nhận profile có host preference như mong muốn
- redeploy router nếu prompt hoặc profile vừa đổi
- kiểm tra `gemini_job.preferred_command_hosts` trong dispatch response

## Service Đang Chạy Nhưng Bản Cập Nhật Không Có Hiệu Lực

### Triệu chứng

- `systemctl status` nhìn vẫn ổn
- nhưng hành vi hệ thống vẫn giống code cũ

### Nguyên nhân thường gặp

- source tree đã sync nhưng service chưa restart
- router host dùng synced tree thay vì git checkout

### Cách xử lý

- xác nhận file mới đã thật sự có trên router
- restart `codex-bridge.service`
- verify lại bằng `/health?depth=full` hoặc smoke test theo route
