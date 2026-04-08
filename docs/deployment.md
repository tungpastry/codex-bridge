# Deployment

This document describes how to deploy `codex-bridge` across the intended three-node setup, with MiddayCommander as the first fully managed DevOps target.

## Target Topology

| Node | Address | Purpose |
| --- | --- | --- |
| Mac mini | `192.168.1.7` | operator workstation and Gemini runner |
| UbuntuDesktop | `192.168.1.15` | router host |
| UbuntuServer | `192.168.1.30` | runtime services and logs |

## 1. Deploy the Router on UbuntuDesktop

Clone and install:

```bash
cd /home/nexus
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Recommended `.env` on UbuntuDesktop:

```env
APP_NAME=codex-bridge
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8787
LLM_BACKEND=ollama
LLM_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=gemma3:1b-it-qat
LLM_TIMEOUT_SECONDS=120
PROMPTS_DIR=/home/nexus/codex-bridge/prompts
STORAGE_DIR=/home/nexus/codex-bridge/storage
CORS_ALLOW_ORIGINS_RAW=http://localhost,http://127.0.0.1
ALLOWED_RESTART_SERVICES_RAW=codex-bridge,postgresql,nginx
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
```

For the MiddayCommander milestone, the deployed tree on UbuntuDesktop is allowed to be a synced service checkout under `/home/nexus/codex-bridge`. It does not need to be a full git clone, because the Mac-side deploy wrapper can refresh that tree directly from the local source of truth.

## 2. Install the systemd Unit

```bash
sudo cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

Useful service commands:

```bash
sudo systemctl restart codex-bridge.service
sudo journalctl -u codex-bridge.service -n 100 --no-pager
curl -sS http://127.0.0.1:8787/health | jq .
```

## 3. Confirm LAN Reachability

From the Mac mini:

```bash
curl -sS http://192.168.1.15:8787/health | jq .
```

If this times out:

- check `ufw` or any other local firewall
- confirm the service is listening on `0.0.0.0:8787`
- confirm the host IP is still `192.168.1.15`

## 4. Prepare the Mac mini

Clone the repo on the Mac:

```bash
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Recommended Mac additions to `.env`:

```env
CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787
CODEX_BRIDGE_GEMINI_BIN=/opt/homebrew/bin/gemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
CODEX_BRIDGE_ALLOWED_RESTART_SERVICES=codex-bridge,postgresql,nginx
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS=180
```

Also confirm:

- Gemini CLI works locally
- Homebrew Python is available
- `jq`, `curl`, and `ssh` are installed
- Remote Login is enabled if UbuntuDesktop will push jobs to the Mac

Create the MiddayCommander target override file on the Mac if you need local custom values:

```bash
cp targets/middaycommander.env.example targets/middaycommander.env
```

Important target defaults:

```env
MIDDAY_MAC_ROOT=/Users/macadmin/Documents/New project/MiddayCommander
MIDDAY_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
MIDDAY_ROUTER_BASE_URL=http://192.168.1.15:8787
MIDDAY_DESKTOP_SSH=nexus@192.168.1.15
MIDDAY_SERVER_SSH=nexus@192.168.1.30
MIDDAY_SERVER_ROOT=/home/nexus/projects/MiddayCommander
MIDDAY_ROUTER_SERVICE=codex-bridge.service
MIDDAY_RELEASE_REPO=tungpastry/MiddayCommander
MIDDAY_RELEASES_ROOT=/home/nexus/releases/middaycommander
MIDDAY_RELEASE_BINARY_NAME=mdc
MIDDAY_RELEASE_SERVER_OS=linux
MIDDAY_RELEASE_SERVER_ARCH=amd64
```

## 5. Configure SSH Alias From UbuntuDesktop to Mac

Add to `~/.ssh/config` on UbuntuDesktop:

```sshconfig
Host MacMiniGemini
  HostName 192.168.1.7
  User macadmin
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking accept-new
```

Then test:

```bash
ssh MacMiniGemini 'hostname && whoami'
```

Expected output should identify the Mac and the `macadmin` user.

## 6. Push-Path Setup

`scripts/push_gemini_to_mac.sh` reads `CODEX_BRIDGE_PUSH_SSH_ALIAS` and `CODEX_BRIDGE_MAC_ROOT` from the repo `.env`.

Once configured, UbuntuDesktop can push a prepared job to the Mac with:

```bash
cd /home/nexus/codex-bridge
./scripts/push_gemini_to_mac.sh --job-file storage/gemini_runs/manual-push-test-job.json
```

## 7. Optional Ollama Preparation

The router is heuristic-first, so Ollama is optional in v1. If you do run it:

- keep it local to UbuntuDesktop
- treat it as refinement, not a hard dependency
- do not let router availability depend on model reachability

## 8. Upgrade Flow

Typical generic upgrade flow:

```bash
cd /home/nexus/codex-bridge
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

For Mac-side runner updates:

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
```

MiddayCommander-specific deploy flow from the Mac mini:

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
./scripts/mac/middaycommander-deploy-router.sh
```

This wrapper:

- syncs the local `codex-bridge` source tree to `/home/nexus/codex-bridge` on `192.168.1.15`
- preserves the remote `.env`
- refreshes `.venv`
- reinstalls the systemd unit
- restarts `codex-bridge.service`
- verifies both local and LAN health

## 9. MiddayCommander Release Flow

Release prerequisites on the Mac mini:

- `gh` installed and authenticated for `tungpastry/MiddayCommander`
- `goreleaser` installed
- a clean MiddayCommander worktree
- an annotated release tag pointing at `HEAD`

Release wrapper usage:

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
./scripts/mac/middaycommander-release.sh --tag v0.3 --dry-run
./scripts/mac/middaycommander-release.sh --tag v0.3
```

This wrapper:

- validates the local tag and repo state on the Mac
- runs `go test ./...` and `go build ./...`
- runs `goreleaser build --clean`
- packages archives and `checksums.txt` locally
- creates a GitHub release in `tungpastry/MiddayCommander`
- promotes the Linux `amd64` artifact to `/home/nexus/releases/middaycommander`
- updates `/home/nexus/releases/middaycommander/current` to the new release
- verifies `current/mdc --version`

The promoted server layout is:

```text
/home/nexus/releases/middaycommander/
├── current -> releases/<tag>
└── releases/
    └── <tag>/
        ├── mdc
        ├── checksums.txt
        └── metadata.json
```

v1 intentionally does not restart any MiddayCommander service on UbuntuServer.

## 10. Post-Deploy Verification

Router checks:

- `curl -sS http://127.0.0.1:8787/health | jq .`
- `curl -sS http://192.168.1.15:8787/health | jq .`

Mac script checks:

- `./scripts/mac/codex-bridge-health.sh`
- `./scripts/mac/middaycommander-health.sh`
- `./scripts/mac/middaycommander-morning-check.sh`
- `./scripts/mac/codex-bridge-daily-report.sh "done: router healthy" "next: review logs"`
- `./scripts/mac/middaycommander-release.sh --tag v0.3 --dry-run`

Expected MiddayCommander outcomes:

- router reachable from the Mac at `http://192.168.1.15:8787/health`
- `codex-bridge.service` active on `192.168.1.15`
- `~/projects/MiddayCommander` present on `192.168.1.30`
- MiddayCommander branch, head, and worktree cleanliness visible in the health output
- promoted release root, current symlink target, and binary version visible in the health output

Gemini push-path check:

- dispatch or build a sample `gemini_job`
- push it with `scripts/push_gemini_to_mac.sh`
- confirm artifacts appear under `storage/gemini_runs/`
