CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  job_id TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  route TEXT NOT NULL,
  input_kind TEXT NOT NULL,
  repo TEXT,
  profile_name TEXT,
  title TEXT NOT NULL,
  task_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  problem_summary TEXT,
  next_step TEXT,
  blocked_flag INTEGER NOT NULL DEFAULT 0,
  timeout_flag INTEGER NOT NULL DEFAULT 0,
  interrupted_flag INTEGER NOT NULL DEFAULT 0,
  needs_human_flag INTEGER NOT NULL DEFAULT 0,
  block_reason TEXT,
  artifact_dir TEXT,
  request_snapshot_path TEXT,
  response_snapshot_path TEXT,
  final_artifact_path TEXT,
  timing_total_ms INTEGER NOT NULL DEFAULT 0,
  timing_model_ms INTEGER NOT NULL DEFAULT 0,
  timing_exec_ms INTEGER NOT NULL DEFAULT 0,
  command_count INTEGER NOT NULL DEFAULT 0,
  actor TEXT,
  source TEXT,
  schema_version TEXT NOT NULL DEFAULT '1'
);

CREATE TABLE IF NOT EXISTS run_commands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  host TEXT NOT NULL,
  command_id TEXT NOT NULL,
  reason TEXT,
  shell_command TEXT,
  status TEXT NOT NULL,
  exit_code INTEGER,
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  truncated_flag INTEGER NOT NULL DEFAULT 0,
  stdout_excerpt TEXT,
  stderr_excerpt TEXT,
  output_path TEXT,
  FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  rule_name TEXT NOT NULL,
  rule_type TEXT NOT NULL,
  matched_value TEXT,
  effect TEXT NOT NULL,
  note TEXT,
  FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  path TEXT NOT NULL,
  content_type TEXT,
  created_at TEXT NOT NULL,
  size_bytes INTEGER,
  sha256 TEXT,
  FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);
