# Hướng Dẫn: Từ Task Code Tới Codex Brief

Tài liệu này minh họa đường đi chuẩn cho các task thiên về implementation.

Tài liệu liên quan:

- [Luồng công việc](../workflow-vi.md)
- [API Reference tiếng Việt](../api-reference-vi.md)
- [English version](./coding-task.md)

## Mục tiêu

Biến một task code còn lộn xộn thành brief sạch để paste vào Codex App.

## Tình huống ví dụ

Bạn có một bug trong `ExampleService`:

- title: `Retry loop panic`
- context: `Tests fail after retry exhaustion in the transfer path`
- constraint: `keep the patch small`

## Bước 1: Lưu raw context

```bash
cat > /tmp/example-retry-panic.txt <<'EOF'
Tests fail after retry exhaustion in the transfer path.
The panic appears after retries are exhausted.
Keep the patch small and avoid redesigning the retry logic.
EOF
```

## Bước 2: Tạo brief

```bash
./scripts/mac/codex-bridge-make-brief.sh \
  "Fix ExampleService retry panic" \
  "ExampleService" \
  /tmp/example-retry-panic.txt
```

## Bước 3: Xem Markdown đã sinh

Output nên có:

- task summary
- repo
- task type
- goal
- constraints
- acceptance criteria
- likely files

## Bước 4: Paste vào Codex App

Paste Markdown đã sinh vào Codex App và tiếp tục implementation theo cách thủ công.

## Tùy chọn: Dùng Dispatch

```bash
./scripts/mac/codex-bridge-dispatch.sh \
  task \
  "Fix ExampleService retry panic" \
  ExampleService \
  /tmp/example-retry-panic.txt
```

Nếu route là `codex`, dùng `codex_brief_markdown`. Nếu route là `human`, dừng lại và review escalation reason.
