from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@dataclass(slots=True)
class DatabaseMigrationInfo:
    db_path: str
    current_user_version: int
    applied_migrations: list[str]
    final_user_version: int


def _migration_files() -> list[tuple[int, Path]]:
    files: list[tuple[int, Path]] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        version = int(path.name.split("_", 1)[0])
        files.append((version, path))
    return files


def apply_index_migrations(db_path: Path) -> DatabaseMigrationInfo:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    applied: list[str] = []

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        for version, path in _migration_files():
            if version <= current_version:
                continue
            connection.executescript(path.read_text(encoding="utf-8"))
            connection.execute(f"PRAGMA user_version = {version}")
            applied.append(path.name)
        final_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        connection.commit()

    return DatabaseMigrationInfo(
        db_path=str(db_path),
        current_user_version=current_version,
        applied_migrations=applied,
        final_user_version=final_version,
    )


def current_user_version(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])
