from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def save_json_snapshot(storage_dir: Path, bucket: str, prefix: str, payload: Any) -> Path:
    filename = "{timestamp}-{prefix}-{token}.json".format(
        timestamp=timestamp_slug(),
        prefix=prefix,
        token=uuid4().hex[:8],
    )
    return write_json(storage_dir / bucket / filename, payload)


def save_text_snapshot(storage_dir: Path, bucket: str, prefix: str, content: str, extension: str = ".md") -> Path:
    filename = "{timestamp}-{prefix}-{token}{extension}".format(
        timestamp=timestamp_slug(),
        prefix=prefix,
        token=uuid4().hex[:8],
        extension=extension,
    )
    return write_text(storage_dir / bucket / filename, content)
