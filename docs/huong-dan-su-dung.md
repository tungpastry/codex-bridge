# Hướng Dẫn Sử Dụng Codex Bridge Cho Người Mới

Tài liệu này dành cho người mới bắt đầu với `codex-bridge`. Mục tiêu là giúp bạn hiểu:

- `codex-bridge` là gì
- khi nào nên dùng `codex`, `gemini`, `human`, hoặc `local`
- cách chạy hệ thống lần đầu
- cách dùng các lệnh cơ bản hằng ngày
- cách nhìn kết quả mà không bị rối

Bạn không cần hiểu toàn bộ codebase trước khi dùng tài liệu này.

## 1. `codex-bridge` là gì?

Hiểu đơn giản, `codex-bridge` là một lớp trung gian để xử lý yêu cầu trước khi đưa việc cho đúng công cụ.

Nó nhận các loại input như:

- task thô
- lỗi build hoặc test
- log hệ thống
- `git diff`
- ghi chú hằng ngày

Sau đó nó quyết định nên đưa việc đó cho ai:

- `codex`: khi việc thiên về sửa code, viết tính năng, review patch
- `gemini`: khi việc thiên về kiểm tra service, log, vận hành, checklist
- `human`: khi việc có rủi ro cao, liên quan production, auth, firewall, schema, dữ liệu
- `local`: khi chỉ cần tóm tắt hoặc format đơn giản

## 2. Hệ thống chạy trên máy nào?

`codex-bridge` đang được thiết kế cho 3 node:

### Mac mini `192.168.1.7`

Đây là máy bạn dùng hằng ngày để:

- mở Codex App
- chạy Gemini CLI
- chạy các script trong `scripts/mac/`

### UbuntuDesktop `192.168.1.15`

Đây là máy chạy FastAPI service `codex-bridge`.

Nó chịu trách nhiệm:

- nhận request
- classify task
- summarize log
- summarize diff
- build Codex brief
- build Gemini job

### UbuntuServer `192.168.1.30`

Đây là máy runtime thật:

- app services
- PostgreSQL
- cron jobs
- `systemd`
- log production hoặc staging

## 3. Luồng làm việc rất ngắn gọn

### Nếu là việc code

1. Chuẩn bị context.
2. Dùng `codex-bridge` để tạo brief.
3. Paste brief đó vào Codex App.
4. Sửa code thủ công trong Codex App hoặc editor.

### Nếu là việc ops

1. Lấy log hoặc mô tả sự cố.
2. Cho `codex-bridge` summarize và dispatch.
3. Nếu route là `gemini`, Mac mini sẽ chạy Gemini CLI headless.
4. Gemini chỉ được phép trả về plan JSON an toàn.
5. Hệ thống chỉ chạy các lệnh đã whitelist.

### Nếu là việc nguy hiểm

Hệ thống sẽ chặn và route sang `human`.

Ví dụ:

- đổi auth production
- đổi firewall
- migration schema production
- xóa dữ liệu
- rotate secret

## 4. Chạy lần đầu như thế nào?

Nếu bạn đang ở repo local:

```bash
cd "/Users/macadmin/Documents/New project/codex-bridge"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./scripts/run_dev.sh
```

Nếu app chạy thành công, bạn sẽ thấy dòng gần giống:

```text
Uvicorn running on http://0.0.0.0:8787
Application startup complete.
```

## 5. Kiểm tra app có sống không

Đây là lệnh đơn giản nhất:

```bash
curl -sS http://127.0.0.1:8787/health | jq .
```

Nếu chạy qua LAN tới `UbuntuDesktop`:

```bash
curl -sS http://192.168.1.15:8787/health | jq .
```

Kết quả tốt sẽ giống kiểu:

```json
{
  "status": "ok",
  "service": "codex-bridge",
  "llm_backend": "ollama",
  "model": "gemma3:1b-it-qat",
  "time": "2026-04-08T06:19:11Z"
}
```

Nếu chưa ra `status: "ok"` thì đừng chạy tiếp các bước khác.

## 6. Dùng `codex-bridge` để xử lý việc code

Đây là use case đơn giản và quan trọng nhất cho người mới.

### Cách 1: tạo Codex brief trực tiếp

Tạo một file context:

```bash
cat > /tmp/task.txt <<'EOF'
Go test đang fail với panic sau khi retry remote transfer bị hết lượt.
Giữ patch nhỏ.
Không redesign retry engine.
EOF
```

Sau đó gọi:

```bash
./scripts/mac/codex-bridge-make-brief.sh \
  "Fix MiddayCommander transfer retry panic" \
  "MiddayCommander" \
  /tmp/task.txt
```

Output sẽ là Markdown. Bạn chỉ cần copy và paste vào Codex App.

### Cách 2: dùng dispatch

Nếu bạn muốn hệ thống tự decide route:

```bash
./scripts/mac/codex-bridge-auto.sh \
  task \
  "Fix MiddayCommander transfer retry panic" \
  "MiddayCommander" \
  /tmp/task.txt
```

Nếu route là `codex`, script sẽ in ra brief.

## 7. Dùng `codex-bridge` để xử lý log

Ví dụ bạn muốn xem log của một service trên `UbuntuServer`:

```bash
./scripts/mac/codex-bridge-triage-log.sh cron.service
```

Script này sẽ:

1. SSH vào `UbuntuServer`
2. lấy `journalctl`
3. gửi log vào `/v1/summarize/log`
4. in JSON đã tóm tắt

Bạn nên nhìn các field sau:

- `symptom`
- `likely_cause`
- `important_lines`
- `recommended_tool`
- `next_step`

Nếu `recommended_tool` là `codex`, thường nghĩa là vấn đề có vẻ là bug code.

Nếu `recommended_tool` là `gemini`, bạn có thể chuyển sang luồng automation an toàn.

## 8. Dùng `codex-bridge` để xử lý diff

Khi bạn đang ở một repo git local và muốn hỏi “diff này có nguy hiểm không?”:

```bash
./scripts/mac/codex-bridge-summarize-diff.sh /duong/dan/toi/repo
```

Kết quả sẽ giúp bạn biết:

- diff này có đụng config không
- có đụng auth không
- có đụng database hoặc migration không
- mức risk đơn giản là `low`, `medium`, hay `high`
- nên đưa cho `codex`, `gemini`, hay `human`

## 9. Dùng `codex-bridge` cho daily report

Ví dụ nhanh:

```bash
./scripts/mac/codex-bridge-daily-report.sh \
  "done: fixed router startup issue" \
  "open: Gemini run is slow" \
  "next: test push path again"
```

Bạn sẽ nhận được report Markdown với 3 phần:

- `Done`
- `Open Issues`
- `Next Actions`

## 10. Khi nào nên dùng `auto.sh`?

`codex-bridge-auto.sh` là entrypoint dễ nhớ nhất cho người mới.

Bạn dùng nó khi muốn:

- đưa context vào một lần
- để hệ thống tự route
- nếu là `codex` thì nhận brief
- nếu là `gemini` thì tự chạy Gemini headless
- nếu là `human` thì dừng và báo lý do

Ví dụ:

```bash
./scripts/mac/codex-bridge-auto.sh \
  task \
  "Check codex-bridge service" \
  "codex-bridge" \
  /tmp/task.txt
```

## 11. Kết quả Gemini nên đọc như thế nào?

Nếu route là `gemini`, kết quả cuối cùng thường có:

- `summary`
- `confidence`
- `final_markdown`
- `timing_summary`
- `timing`

### `timing_summary` dùng để làm gì?

Nó giúp bạn biết rõ:

- Gemini CLI mất bao lâu
- phần safe command execution mất bao lâu
- tổng pipeline mất bao lâu

Ví dụ:

```text
Gemini CLI: 71.0s | Safe exec: 0.8s | Total: 72.1s
```

Điều này rất hữu ích vì bạn sẽ biết bottleneck nằm ở Gemini hay ở bước chạy lệnh.

## 12. File kết quả của Gemini nằm ở đâu?

Nằm trong:

```text
storage/gemini_runs/
```

Một run thường có các file:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

Nếu bạn muốn debug một run bị chậm hoặc bị block, đây là nơi nên xem đầu tiên.

## 13. Những script quan trọng nhất cho người mới

Nếu chỉ nhớ vài script đầu tiên, hãy nhớ các file này:

### Kiểm tra health

```bash
./scripts/mac/codex-bridge-health.sh
```

### Triage log

```bash
./scripts/mac/codex-bridge-triage-log.sh <ten-service>
```

### Tạo Codex brief

```bash
./scripts/mac/codex-bridge-make-brief.sh "<title>" "<repo>" <context-file>
```

### Dispatch hoặc auto route

```bash
./scripts/mac/codex-bridge-auto.sh <input-kind> "<title>" "<repo>" <context-file>
```

### Daily report

```bash
./scripts/mac/codex-bridge-daily-report.sh "done: ..." "open: ..." "next: ..."
```

## 14. Những lỗi người mới hay gặp

### Lỗi 1: app không lên

Hãy kiểm tra:

- đã `source .venv/bin/activate` chưa
- đã `pip install -r requirements.txt` chưa
- `.env` có tồn tại không

### Lỗi 2: Mac gọi không tới `192.168.1.15:8787`

Hãy kiểm tra:

- service trên `UbuntuDesktop` đã chạy chưa
- firewall có đang chặn port `8787` không
- bạn có gọi đúng IP LAN không

### Lỗi 3: `push_gemini_to_mac.sh` báo lỗi với `<path-to-gemini-job.json>`

Đó chỉ là placeholder.

Bạn phải thay bằng đường dẫn thật, ví dụ:

```bash
./scripts/push_gemini_to_mac.sh --job-file storage/gemini_runs/manual-push-test-job.json
```

### Lỗi 4: Gemini chạy rất lâu

Hãy xem:

- `timing_summary`
- file `storage/gemini_runs/<run_id>-timing.json`

Đừng đoán mò. Hãy nhìn timing thật.

## 15. Khi nào nên dừng automation ngay?

Bạn nên dừng và tự kiểm tra khi thấy:

- route là `human`
- task liên quan auth, firewall, secret, schema production
- có ý định xóa dữ liệu
- có dấu hiệu runner bị block vì command không nằm trong whitelist

Nguyên tắc quan trọng:

`codex-bridge` được thiết kế để chặn việc nguy hiểm, không phải để cố tự động hóa mọi thứ bằng mọi giá.

## 16. Bắt đầu từ đâu nếu bạn hoàn toàn mới?

Nếu bạn chỉ muốn bắt đầu mà không suy nghĩ nhiều, đi theo đúng thứ tự này:

1. chạy health check
2. chạy `codex-bridge-make-brief.sh` với một task code đơn giản
3. chạy `codex-bridge-triage-log.sh` với một service an toàn như `cron.service`
4. chạy `codex-bridge-daily-report.sh` với vài dòng mẫu
5. sau đó mới dùng `codex-bridge-auto.sh`

Đây là lộ trình học nhanh và ít rủi ro nhất.

## 17. Tài liệu nên đọc tiếp

Sau khi đọc xong file này, bạn nên đọc tiếp:

- `docs/architecture.md` nếu muốn hiểu hệ 3 node
- `docs/api-reference.md` nếu muốn gọi API trực tiếp
- `docs/deployment.md` nếu muốn deploy bài bản
- `docs/troubleshooting.md` nếu đang gặp lỗi
- `docs/tutorials/coding-task.md` nếu muốn flow code rõ hơn
- `docs/tutorials/ops-incident.md` nếu muốn flow ops rõ hơn

## 18. Tóm tắt một câu

Nếu phải nhớ một điều duy nhất, hãy nhớ:

`codex-bridge` giúp bạn đưa đúng việc cho đúng công cụ, với ít mơ hồ hơn và ít rủi ro hơn.
