from __future__ import annotations

import hashlib
from pathlib import Path

from app.utils.files import iso_now


CONTENT_TYPES = {
    ".json": "application/json",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_record(run_id: str, artifact_type: str, path: str | Path) -> dict[str, object]:
    artifact_path = Path(path)
    return {
        "run_id": run_id,
        "artifact_type": artifact_type,
        "path": str(artifact_path),
        "content_type": CONTENT_TYPES.get(artifact_path.suffix.lower(), "application/octet-stream"),
        "created_at": iso_now(),
        "size_bytes": artifact_path.stat().st_size if artifact_path.exists() else 0,
        "sha256": _sha256(artifact_path) if artifact_path.exists() else "",
    }
