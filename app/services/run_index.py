from __future__ import annotations

from app.core.settings import Settings
from app.index.manager import apply_index_migrations
from app.index.repository import RunIndexRepository


def get_run_index(settings: Settings) -> RunIndexRepository:
    settings.ensure_runtime_dirs()
    apply_index_migrations(settings.run_index_db_path)
    return RunIndexRepository(settings.run_index_db_path)
