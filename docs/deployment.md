# Deployment

Tai lieu nay mo ta cach deploy `codex-bridge` sau Production Upgrade Blueprint v1.

## Topology muc tieu

| Node | Dia chi | Muc dich |
| --- | --- | --- |
| Mac mini | `192.168.1.7` | Codex App, Gemini CLI runner |
| UbuntuDesktop | `192.168.1.15` | router host, SQLite run index owner |
| UbuntuServer | `192.168.1.30` | app runtime, postgres, logs |

## 1. Deploy router tren UbuntuDesktop

```bash
cd /home/nexus
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Bien moi quan trong trong `.env`:

```env
APP_NAME=codex-bridge
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8787

PROMPTS_DIR=/home/nexus/codex-bridge/prompts
STORAGE_DIR=/home/nexus/codex-bridge/storage
RUN_INDEX_DB_PATH=/home/nexus/codex-bridge/storage/index/runs.db
PROFILES_DIR=/home/nexus/codex-bridge/app/profiles

CORS_ALLOW_ORIGINS_RAW=http://localhost,http://127.0.0.1
ALLOWED_RESTART_SERVICES_RAW=codex-bridge,postgresql,nginx

CODEX_BRIDGE_INTERNAL_API_TOKEN=replace-this-with-a-real-secret
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
```

## 2. Cai systemd unit

```bash
sudo cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

Lenh huu ich:

```bash
sudo systemctl restart codex-bridge.service
sudo journalctl -u codex-bridge.service -n 120 --no-pager
curl -sS http://127.0.0.1:8787/health | jq .
```

## 3. Kiem tra startup migration log

Sau khi service len, log phai co dong migration ro rang. Ban nen thay:

- `db_path=...`
- `current_user_version=...`
- `applied_migrations=...`
- `final_user_version=...`

Vi du:

```bash
journalctl -u codex-bridge.service -n 50 --no-pager | rg run_index_migrations
```

Neu khong co dong nay, qua trinh deploy se kho debug hon rat nhieu.

## 4. Kiem tra LAN reachability

Tu Mac mini:

```bash
curl -sS http://192.168.1.15:8787/health | jq .
curl -sS http://192.168.1.15:8787/health?depth=full | jq .
```

Neu timeout:

- check firewall/UFW
- xac nhan service nghe tren `0.0.0.0:8787`
- xac nhan IP van la `192.168.1.15`

## 5. Chuan bi Mac mini

```bash
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Bien uu tien tren Mac:

```env
CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787
CODEX_BRIDGE_GEMINI_BIN=/opt/homebrew/bin/gemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
CODEX_BRIDGE_ALLOWED_RESTART_SERVICES=codex-bridge,postgresql,nginx
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS=180
CODEX_BRIDGE_INTERNAL_API_TOKEN=replace-this-with-the-same-secret-as-router
```

Hay dam bao:

- Gemini CLI chay duoc local
- `jq`, `curl`, `ssh` da co
- Remote Login da bat neu UbuntuDesktop se push job sang Mac

## 6. Cau hinh SSH alias tu UbuntuDesktop sang Mac

Tren `UbuntuDesktop:~/.ssh/config`:

```sshconfig
Host MacMiniGemini
  HostName 192.168.1.7
  User macadmin
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking accept-new
```

Test:

```bash
ssh MacMiniGemini 'hostname && whoami'
```

## 7. Router push path

`scripts/push_gemini_to_mac.sh` doc:

- `CODEX_BRIDGE_PUSH_SSH_ALIAS`
- `CODEX_BRIDGE_MAC_ROOT`

tu `.env` cua repo tren UbuntuDesktop.

Chay test:

```bash
cd /home/nexus/codex-bridge
./scripts/push_gemini_to_mac.sh --job-file storage/gemini_runs/manual-push-test-job.json
```

## 8. Internal callback token

Mac runner se post execution callback ve router bang:

- `POST /v1/internal/runs/{run_id}/execution`

Vi vay:

- token tren Mac va UbuntuDesktop phai giong nhau
- token khong nen de mac dinh khi chay production
- token nay chi dung cho callback noi bo

## 9. Upgrade flow

Router host:

```bash
cd /home/nexus/codex-bridge
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

Mac runner:

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
```

## 10. Kiem tra sau deploy

Nen chay toi thieu:

```bash
curl -sS http://127.0.0.1:8787/health | jq .
curl -sS http://127.0.0.1:8787/health?depth=full | jq .
curl -sS http://127.0.0.1:8787/v1/admin/metrics | jq .
curl -sS http://127.0.0.1:8787/v1/runs?limit=5 | jq .
```

Neu can smoke nhanh luong Gemini:

```bash
./scripts/mac/codex-bridge-auto.sh task "Inspect codex-bridge health" codex-bridge /path/to/context.txt
```

## 11. Ghi chu ve rollback

V1 van giu he thong don gian:

- khong queue
- khong Redis
- khong DB service ngoai SQLite index
- khong background worker phuc tap

Rollback co ban la:

1. checkout commit cu
2. reinstall requirements neu can
3. restart systemd unit

SQLite run index co the duoc giu lai an toan vi migrations hien tai chi mo rong read/query surface, khong can worker migration rieng.
