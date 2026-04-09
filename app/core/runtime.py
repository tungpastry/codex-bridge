from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.settings import Settings
from app.index.manager import DatabaseMigrationInfo, apply_index_migrations
from app.profiles.loader import load_profiles


LOGGER = logging.getLogger("codex_bridge.runtime")


@dataclass(slots=True)
class RuntimeState:
    migration_info: DatabaseMigrationInfo
    profile_names: list[str]


def bootstrap_runtime(settings: Settings) -> RuntimeState:
    settings.ensure_runtime_dirs()
    migration_info = apply_index_migrations(settings.run_index_db_path)
    LOGGER.info(
        "run_index_migrations db_path=%s current_user_version=%s applied_migrations=%s final_user_version=%s",
        migration_info.db_path,
        migration_info.current_user_version,
        ",".join(migration_info.applied_migrations) if migration_info.applied_migrations else "none",
        migration_info.final_user_version,
    )
    profiles = load_profiles(settings.profiles_dir)
    return RuntimeState(
        migration_info=migration_info,
        profile_names=sorted(profiles.keys()),
    )
