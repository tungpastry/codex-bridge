CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_repo ON runs(repo);
CREATE INDEX IF NOT EXISTS idx_runs_route ON runs(route);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_run_rules_run_id ON run_rules(run_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_run_commands_run_ordinal ON run_commands(run_id, ordinal);
CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_run_type_path ON artifacts(run_id, artifact_type, path);
CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);
