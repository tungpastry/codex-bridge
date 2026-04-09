from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class RunIndexRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def create_run(self, payload: dict[str, Any]) -> None:
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO runs ({columns}) VALUES ({placeholders})",
                payload,
            )
            connection.commit()

    def update_run(self, run_id: str, payload: dict[str, Any]) -> None:
        if not payload:
            return
        assignments = ", ".join(f"{key} = :{key}" for key in payload)
        data = dict(payload)
        data["run_id"] = run_id
        with self._connect() as connection:
            connection.execute(
                f"UPDATE runs SET {assignments} WHERE run_id = :run_id",
                data,
            )
            connection.commit()

    def replace_run_rules(self, run_id: str, rules: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM run_rules WHERE run_id = ?", (run_id,))
            for rule in rules:
                connection.execute(
                    """
                    INSERT INTO run_rules (
                      run_id, rule_name, rule_type, matched_value, effect, note
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        rule["rule_name"],
                        rule["rule_type"],
                        rule.get("matched_value"),
                        rule["effect"],
                        rule.get("note"),
                    ),
                )
            connection.commit()

    def upsert_run_commands(self, run_id: str, commands: list[dict[str, Any]]) -> None:
        if not commands:
            return
        with self._connect() as connection:
            for command in commands:
                payload = dict(command)
                payload["run_id"] = run_id
                connection.execute(
                    """
                    INSERT INTO run_commands (
                      run_id, ordinal, host, command_id, reason, shell_command, status,
                      exit_code, started_at, finished_at, duration_ms, truncated_flag,
                      stdout_excerpt, stderr_excerpt, output_path
                    ) VALUES (
                      :run_id, :ordinal, :host, :command_id, :reason, :shell_command, :status,
                      :exit_code, :started_at, :finished_at, :duration_ms, :truncated_flag,
                      :stdout_excerpt, :stderr_excerpt, :output_path
                    )
                    ON CONFLICT(run_id, ordinal) DO UPDATE SET
                      host = excluded.host,
                      command_id = excluded.command_id,
                      reason = excluded.reason,
                      shell_command = excluded.shell_command,
                      status = excluded.status,
                      exit_code = excluded.exit_code,
                      started_at = excluded.started_at,
                      finished_at = excluded.finished_at,
                      duration_ms = excluded.duration_ms,
                      truncated_flag = excluded.truncated_flag,
                      stdout_excerpt = excluded.stdout_excerpt,
                      stderr_excerpt = excluded.stderr_excerpt,
                      output_path = excluded.output_path
                    """,
                    payload,
                )
            connection.commit()

    def upsert_artifacts(self, artifacts: list[dict[str, Any]]) -> None:
        if not artifacts:
            return
        with self._connect() as connection:
            for artifact in artifacts:
                connection.execute(
                    """
                    INSERT INTO artifacts (
                      run_id, artifact_type, path, content_type, created_at, size_bytes, sha256
                    ) VALUES (
                      :run_id, :artifact_type, :path, :content_type, :created_at, :size_bytes, :sha256
                    )
                    ON CONFLICT(run_id, artifact_type, path) DO UPDATE SET
                      content_type = excluded.content_type,
                      created_at = excluded.created_at,
                      size_bytes = excluded.size_bytes,
                      sha256 = excluded.sha256
                    """,
                    artifact,
                )
            connection.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def get_run_rules(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT rule_name, rule_type, matched_value, effect, note FROM run_rules WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        return self._rows(rows)

    def get_run_commands(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM run_commands WHERE run_id = ? ORDER BY ordinal ASC",
                (run_id,),
            ).fetchall()
        return self._rows(rows)

    def get_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT artifact_type, path, content_type, created_at, size_bytes, sha256 FROM artifacts WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        return self._rows(rows)

    def list_runs(
        self,
        *,
        repo: str = "",
        route: str = "",
        status: str = "",
        date: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        filters: list[str] = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if repo:
            filters.append("repo = :repo")
            params["repo"] = repo
        if route:
            filters.append("route = :route")
            params["route"] = route
        if status:
            filters.append("status = :status")
            params["status"] = status
        if date:
            filters.append("substr(created_at, 1, 10) = :date")
            params["date"] = date
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        with self._connect() as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM runs {where_sql}", params).fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT run_id, job_id, created_at, finished_at, status, route, input_kind, repo, profile_name,
                       title, task_type, severity, problem_summary, next_step, blocked_flag, timeout_flag,
                       interrupted_flag, needs_human_flag, block_reason, artifact_dir, request_snapshot_path,
                       response_snapshot_path, final_artifact_path, timing_total_ms, timing_model_ms,
                       timing_exec_ms, command_count, actor, source, schema_version
                FROM runs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """,
                params,
            ).fetchall()

        return {
            "items": self._rows(rows),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def metrics(self, *, date: str) -> dict[str, Any]:
        with self._connect() as connection:
            runs_total = int(connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
            runs_today = int(
                connection.execute("SELECT COUNT(*) FROM runs WHERE substr(created_at, 1, 10) = ?", (date,)).fetchone()[0]
            )
            blocked_today = int(
                connection.execute(
                    "SELECT COUNT(*) FROM runs WHERE substr(created_at, 1, 10) = ? AND blocked_flag = 1",
                    (date,),
                ).fetchone()[0]
            )
            timeouts_today = int(
                connection.execute(
                    "SELECT COUNT(*) FROM runs WHERE substr(created_at, 1, 10) = ? AND timeout_flag = 1",
                    (date,),
                ).fetchone()[0]
            )
            route_rows = connection.execute(
                "SELECT route, COUNT(*) AS count FROM runs GROUP BY route ORDER BY route ASC"
            ).fetchall()
            timing_row = connection.execute(
                """
                SELECT
                  COALESCE(AVG(timing_total_ms), 0) AS total_ms,
                  COALESCE(AVG(timing_model_ms), 0) AS model_ms,
                  COALESCE(AVG(timing_exec_ms), 0) AS exec_ms
                FROM runs
                """
            ).fetchone()

        return {
            "runs_total": runs_total,
            "runs_today": runs_today,
            "blocked_today": blocked_today,
            "timeouts_today": timeouts_today,
            "route_distribution": {row["route"]: row["count"] for row in route_rows},
            "average_timing_ms": {
                "total": int(timing_row["total_ms"]),
                "model": int(timing_row["model_ms"]),
                "exec": int(timing_row["exec_ms"]),
            },
        }
