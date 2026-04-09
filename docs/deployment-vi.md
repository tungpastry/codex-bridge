# Triển Khai

Tài liệu này mô tả mô hình triển khai hiện tại của `codex-bridge` sau nâng cấp production.

Tài liệu liên quan:

- [README](../README.md)
- [Kiến trúc](./architecture-vi.md)
- [Khắc phục sự cố](./troubleshooting-vi.md)
- [English version](./deployment.md)

## Topology Mục Tiêu

| Node | Địa chỉ | Mục đích |
| --- | --- | --- |
| Mac mini | `192.168.1.7` | Codex App, Gemini CLI runner, operator scripts |
| UbuntuDesktop | `192.168.1.15` | router host, SQLite run index owner |
| UbuntuServer | `192.168.1.30` | runtime node, services, logs, database |

## 1. Deploy Router trên UbuntuDesktop

Flow chuẩn theo git:

```bash
cd /home/nexus
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Các biến `.env` quan trọng trên router:

```env
APP_NAME=codex-bridge
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8787

PROMPTS_DIR=/home/nexus/codex-bridge/prompts
STORAGE_DIR=/home/nexus/codex-bridge/storage
RUN_INDEX_DB_PATH=/home/nexus/codex-bridge/storage/index/runs.db
PROFILES_DIR=/home/nexus/codex-bridge/app/profiles

LLM_BACKEND=ollama
LLM_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=gemma3:1b-it-qat

CORS_ALLOW_ORIGINS_RAW=http://localhost,http://127.0.0.1
ALLOWED_RESTART_SERVICES_RAW=codex-bridge,postgresql,nginx
CODEX_BRIDGE_INTERNAL_API_TOKEN=replace-with-a-real-secret
```

Nếu router host của bạn được cập nhật bằng sync source tree thay vì `git pull`, hãy giữ nguyên layout thư mục và biến môi trường, sau đó restart service sau khi sync.

## 2. Cài systemd Unit

```bash
sudo cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

Một số lệnh hay dùng:

```bash
sudo systemctl restart codex-bridge.service
sudo journalctl -u codex-bridge.service -n 120 --no-pager
curl -sS http://127.0.0.1:8787/health | jq .
curl -sS http://127.0.0.1:8787/health?depth=full | jq .
```

## 3. Kiểm Tra Startup Migration Log

Khi startup, router phải log chi tiết migration của SQLite run index. Bạn nên thấy các giá trị như:

- `db_path`
- `current_user_version`
- `applied_migrations`
- `final_user_version`

Ví dụ:

```bash
journalctl -u codex-bridge.service -n 80 --no-pager | rg run_index_migrations
```

Đây là log rất quan trọng khi debug upgrade, tạo DB mới, hoặc cấu hình sai đường dẫn storage.

## 4. Kiểm Tra LAN Reachability

Từ Mac mini:

```bash
curl -sS http://192.168.1.15:8787/health | jq .
curl -sS http://192.168.1.15:8787/health?depth=full | jq .
```

Nếu lỗi:

- xác nhận app đang nghe trên `0.0.0.0:8787`
- kiểm tra UFW hoặc firewall khác
- xác nhận router vẫn dùng IP `192.168.1.15`

## 5. Chuẩn Bị Mac Runner

```bash
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Các biến `.env` nên có trên Mac:

```env
CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787
CODEX_BRIDGE_GEMINI_BIN=/opt/homebrew/bin/gemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
CODEX_BRIDGE_ALLOWED_RESTART_SERVICES=codex-bridge,postgresql,nginx
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS=180
CODEX_BRIDGE_INTERNAL_API_TOKEN=use-the-same-secret-as-the-router
```

Nếu Gemini CLI chạy headless, hãy chắc chắn auth đã sẵn sàng bằng cached credentials hoặc env-based auth.

## 6. Cấu Hình SSH Alias Từ UbuntuDesktop sang Mac

Trên `UbuntuDesktop`, cấu hình `~/.ssh/config`:

```sshconfig
Host MacMiniGemini
  HostName 192.168.1.7
  User macadmin
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking accept-new
```

Kiểm tra:

```bash
ssh MacMiniGemini 'hostname && whoami'
```

## 7. Router Push Path

`scripts/push_gemini_to_mac.sh` sẽ đọc các giá trị sau từ `.env` của repo trên router:

- `CODEX_BRIDGE_PUSH_SSH_ALIAS`
- `CODEX_BRIDGE_MAC_ROOT`

Ví dụ smoke check:

```bash
cd /home/nexus/codex-bridge
./scripts/push_gemini_to_mac.sh --job-file storage/gemini_runs/manual-push-test-job.json
```

## 8. Đồng Bộ Internal Callback Token

Mac runner cập nhật router qua:

- `POST /v1/internal/runs/{run_id}/execution`

Vì vậy:

- token trên Mac và trên router phải giống nhau
- token không nên giữ giá trị dev mặc định khi chạy thật
- nếu token lệch, run index sẽ không được cập nhật dù local execution vẫn thành công

## 9. Upgrade Flow

Flow theo git:

```bash
cd /home/nexus/codex-bridge
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

Cập nhật phía Mac:

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
```

Nếu router của bạn dùng source tree sync thay vì git checkout, hãy thay `git pull` bằng bước sync của bạn rồi restart service.

## 10. Kiểm Tra Sau Deploy

Các check nên chạy trên router:

```bash
curl -sS http://127.0.0.1:8787/health | jq .
curl -sS http://127.0.0.1:8787/health?depth=full | jq .
curl -sS 'http://127.0.0.1:8787/v1/admin/metrics' | jq .
curl -sS 'http://127.0.0.1:8787/v1/runs?limit=5' | jq .
```

Smoke test end-to-end từ Mac:

```bash
./scripts/mac/codex-bridge-auto.sh task \
  "Inspect codex-bridge health" \
  codex-bridge \
  /path/to/context.txt
```

## 11. Ghi Chú Rollback

Hệ thống hiện vẫn cố tình đơn giản:

- không có Redis
- không có queue service
- không có worker fleet riêng
- không có DB thứ hai ngoài SQLite run index trên router

Rollback cơ bản thường là:

1. đưa source tree về commit hoặc bản sync cũ hơn
2. cài lại requirements nếu dependency set có đổi
3. restart `codex-bridge.service`

SQLite run index hiện có thể giữ lại trong đa số trường hợp vì migration hiện tại chỉ mở rộng observability surface, không cần migration service riêng.
