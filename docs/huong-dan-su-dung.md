# Hướng Dẫn Sử Dụng Codex Bridge Cho Người Mới

Tài liệu này dành cho người mới hoàn toàn, cần một đường đi đơn giản để bắt đầu dùng `codex-bridge` mà không phải đọc hết toàn bộ docs kỹ thuật trước.

Tài liệu nên đọc tiếp:

- [README](../README.md)
- [Kiến trúc](./architecture-vi.md)
- [API Reference tiếng Việt](./api-reference-vi.md)
- [Luồng công việc](./workflow-vi.md)
- [Khắc phục sự cố](./troubleshooting-vi.md)

## 1. `codex-bridge` là gì?

`codex-bridge` là một internal routing platform nhỏ gọn giúp bạn đưa đúng loại việc sang đúng luồng xử lý:

- việc code sang `codex`
- việc ops an toàn sang `gemini`
- việc nguy hiểm sang `human`
- việc đơn giản sang `local`

Nó không tự làm mọi thứ. Nó chỉ giúp:

- làm sạch context
- chọn route rõ ràng
- giữ ranh giới an toàn
- lưu lại run và artifact để truy vết

## 2. Hệ thống chạy trên máy nào?

### Mac mini `192.168.1.7`

- máy làm việc của operator
- chạy Codex App
- chạy Gemini CLI
- chạy các script trong `scripts/mac/`

### UbuntuDesktop `192.168.1.15`

- chạy FastAPI router
- giữ prompts, profiles, và run index SQLite
- là nơi bạn query `/v1/runs` và `/v1/admin/metrics`

### UbuntuServer `192.168.1.30`

- chạy service thực tế
- chứa log, systemd service, database, runtime state

## 3. Luồng làm việc rất ngắn gọn

### Nếu là việc code

1. tạo brief
2. paste vào Codex App
3. code và test thủ công

### Nếu là việc ops an toàn

1. dispatch hoặc triage log
2. route sang `gemini`
3. Gemini sinh typed plan
4. chỉ các command an toàn mới được chạy

### Nếu là việc nguy hiểm

1. hệ thống route sang `human`
2. dừng automation
3. review thủ công

## 4. Chạy lần đầu như thế nào?

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./scripts/run_dev.sh
```

## 5. Kiểm tra app có sống không

```bash
curl -sS http://127.0.0.1:8787/health | jq .
curl -sS http://192.168.1.15:8787/health?depth=full | jq .
```

Nếu `depth=full` trả được:

- index DB đang sống
- profiles đã load
- allowed hosts và command catalog đang sẵn sàng

## 6. Dùng `codex-bridge` để xử lý việc code

### Cách 1: tạo Codex brief trực tiếp

```bash
./scripts/mac/codex-bridge-make-brief.sh \
  "Fix transfer retry panic" \
  "ExampleService" \
  /path/to/context.txt
```

### Cách 2: dùng dispatch

```bash
./scripts/mac/codex-bridge-dispatch.sh \
  task \
  "Fix transfer retry panic" \
  ExampleService \
  /path/to/context.txt
```

Nếu route là `codex`, bạn sẽ lấy `codex_brief_markdown`.

## 7. Dùng `codex-bridge` để xử lý log

```bash
./scripts/mac/codex-bridge-triage-log.sh cron.service
```

Bạn sẽ nhận được:

- `symptom`
- `likely_cause`
- `recommended_tool`
- `next_step`

## 8. Dùng `codex-bridge` để xử lý diff

```bash
./scripts/mac/codex-bridge-summarize-diff.sh /path/to/repo
```

Bạn sẽ thấy:

- `summary`
- `risk_level`
- `review_focus`
- `recommended_tool`

## 9. Dùng `codex-bridge` cho daily report

```bash
./scripts/mac/codex-bridge-daily-report.sh /path/to/notes.txt
```

Output sẽ có:

- `Done`
- `Open Issues`
- `Next Actions`

## 10. Khi nào nên dùng `auto.sh`?

Dùng `auto.sh` khi bạn muốn để router tự quyết định route và nếu route là `gemini` thì tiếp tục chạy luôn.

Ví dụ:

```bash
./scripts/mac/codex-bridge-auto.sh \
  task \
  "Inspect service health" \
  codex-bridge \
  /path/to/context.txt
```

## 11. Kết quả Gemini nên đọc như thế nào?

Khi một run Gemini hoàn tất, hãy chú ý:

- `status`
- `summary`
- `why`
- `final_markdown`
- `results[]`
- `timing_summary`

### `timing_summary` dùng để làm gì?

Nó giúp bạn biết độ trễ nằm ở đâu:

- model headless chậm
- safe execution chậm
- hay tổng pipeline chậm

## 12. File kết quả của Gemini nằm ở đâu?

Trong `storage/gemini_runs/`, thường có:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

## 13. Những script quan trọng nhất cho người mới

- `scripts/mac/codex-bridge-health.sh`
- `scripts/mac/codex-bridge-make-brief.sh`
- `scripts/mac/codex-bridge-dispatch.sh`
- `scripts/mac/codex-bridge-auto.sh`
- `scripts/mac/codex-bridge-daily-report.sh`

## 14. Những lỗi người mới hay gặp

### Lỗi 1: app không lên

Xem:

- `journalctl -u codex-bridge.service -n 120 --no-pager`
- [Khắc phục sự cố](./troubleshooting-vi.md)

### Lỗi 2: Mac gọi không tới `192.168.1.15:8787`

- kiểm tra LAN/firewall
- kiểm tra service có đang nghe `0.0.0.0:8787` hay không

### Lỗi 3: Gemini bị block do auth

- xác nhận Gemini CLI headless đã có auth
- xác nhận `.env` có auth phù hợp

### Lỗi 4: callback không cập nhật run index

- xác nhận `CODEX_BRIDGE_BASE_URL`
- xác nhận `CODEX_BRIDGE_INTERNAL_API_TOKEN` giống nhau giữa Mac và router

## 15. Khi nào nên dừng automation ngay?

Dừng ngay nếu:

- route là `human`
- plan bị block
- task đụng tới auth, firewall, schema, secret, hoặc destructive operation

## 16. Bắt đầu từ đâu nếu bạn hoàn toàn mới?

Lộ trình ít rủi ro nhất:

1. chạy `health`
2. thử `make-brief`
3. thử `dispatch`
4. đọc `run_id`, `decision_trace`, `artifacts`
5. sau đó mới dùng `auto.sh`

## 17. Tóm tắt một câu

`codex-bridge` giúp bạn route đúng việc sang đúng luồng, giữ an toàn cho ops automation, và để lại dấu vết rõ ràng cho mọi run quan trọng.
