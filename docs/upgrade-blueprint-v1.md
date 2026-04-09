# Upgrade Blueprint v1

Tai lieu nay tong hop nhung gi da duoc them vao `codex-bridge` trong ban nang cap production v1.

## Muc tieu

Nang cap project tu mot router v1 thuc dung thanh mot internal routing platform production-ready hon, nhung van giu nguyen dinh huong:

- heuristic-first
- fail-closed
- Codex App van la manual paste flow
- Gemini chi duoc thuc thi trong typed safe-command boundary
- run co trace, artifact, va index de query

## Nhung thay doi lon

### 1. Package structure ro hon

Project da duoc tach thanh cac package sau:

- `app/api/routes`
- `app/core`
- `app/policy`
- `app/builders`
- `app/execution`
- `app/artifacts`
- `app/index`
- `app/profiles`
- `app/services`
- `app/schemas`

`app/routes/*` van duoc giu lai lam compatibility wrappers.

### 2. SQLite run index

Run index duoc them vao router host de query lich su run.

Bang chinh:

- `runs`
- `run_commands`
- `run_rules`
- `artifacts`

Migrations:

- `001_init.sql`
- `002_indexes.sql`

Migrations tu apply khi startup va co log migration ro rang.

### 3. Decision trace

Routing khong con la hop den duy nhat. Response classify/log/diff/dispatch hien co:

- `decision_trace.matched_rules`
- `decision_trace.confidence`

Dieu nay giup operator va reviewer hieu vi sao router dua ra quyet dinh.

### 4. Dispatch persistence

`/v1/dispatch/task` hien tai:

- tao `run_id`
- luu request snapshot
- luu run metadata ban dau
- luu matched rules
- luu response snapshot
- luu artifact metadata

Artifact taxonomy da chot:

- `request_snapshot`
- `response_snapshot`
- `codex_brief`
- `daily_report`
- `gemini_job`
- `execution_plan`
- `execution_result`
- `timing`
- `final_result`

### 5. Typed execution model

Execution da duoc typed hoa qua:

- `ExecutionPlan`
- `ExecutionCommand`
- `ExecutionResult`
- `ExecutionBatchResult`
- `ExecutionCallbackRequest`

Gemini khong duoc phep tra shell text tu do. Moi command deu phai di qua:

- `host`
- `command_id`
- `args`
- `reason`

### 6. Internal callback

Mac runner cap nhat ket qua ve router bang internal callback:

- `POST /v1/internal/runs/{run_id}/execution`

Properties:

- co token
- co `phase`
- idempotent khi retry
- khong duplicate `run_commands`

`run_commands` duoc upsert theo `(run_id, ordinal)`.

### 7. Runs va metrics APIs

Da them:

- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/artifacts`
- `GET /v1/admin/metrics`
- `GET /health?depth=full`

`GET /v1/runs` mac dinh sort theo `created_at DESC`.

### 8. Profiles toi gian

Da them profile YAML de lam hint cho repo:

- `codex-bridge.yaml`
- `middaycommander.yaml`

Profiles chi duoc dung de bo sung context, khong duoc pha vo safety policy.

## Vi sao ban nang cap nay quan trong

Truoc day, he thong da chay duoc, nhung con mot so diem mo ho:

- kho tra cuu lich su run
- kho hieu vi sao router ra quyet dinh
- execution result chua duoc normalize ro rang
- docs va test chua phan anh het flow moi

Sau ban nang cap nay, `codex-bridge` van don gian nhung ro hon:

- de debug deploy hon
- de tra cuu incident hon
- de review routing behavior hon
- de audit Gemini safe execution hon

## Cac nguyen tac van duoc giu nguyen

- khong full automation dieu khien Codex App
- khong arbitrary shell tu Gemini
- khong thay heuristic bang mandatory LLM routing
- khong dua Redis/Celery/queue vao v1
- khong over-engineer profile system

## Ghi chu van hanh

Neu ban gap van de sau deploy, uu tien check:

1. `/health?depth=full`
2. startup migration log
3. `/v1/runs?limit=10`
4. artifact files trong `storage/`
5. callback token va SSH path cua Mac runner
