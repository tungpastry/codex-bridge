from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PROMPTS_DIR", str(ROOT / "prompts"))
os.environ.setdefault("STORAGE_DIR", str(ROOT / "storage"))

from fastapi.testclient import TestClient

from app.main import app


def pretty(label: str, payload) -> None:
    print("== {0}".format(label))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    client = TestClient(app)

    pretty("health", client.get("/health").json())
    pretty(
        "classify",
        client.post(
            "/v1/classify/task",
            json={
                "title": "MiddayCommander build failure",
                "context": "Go test failed with panic in remote transfer retry path",
                "repo": "MiddayCommander",
                "source": "smoke",
                "constraints": ["Keep patch small"],
            },
        ).json(),
    )
    pretty(
        "diff summary",
        client.post(
            "/v1/summarize/diff",
            json={
                "repo": "MiddayCommander",
                "diff_text": "diff --git a/internal/fs/router.go b/internal/fs/router.go\n+++ b/internal/fs/router.go\n@@\n+if err != nil { return err }\n",
            },
        ).json(),
    )
    pretty(
        "report",
        client.post(
            "/v1/report/daily",
            json={"items": ["Done: added health route", "Open: need smoke check", "Next: verify dispatch flow"]},
        ).json(),
    )
    brief = client.post(
        "/v1/brief/codex",
        json={
            "title": "Fix MiddayCommander retry panic",
            "repo": "MiddayCommander",
            "context": "Retry path panics after final remote failure",
            "constraints": ["Minimal patch"],
        },
    ).json()
    print("== codex brief")
    print(brief["brief_markdown"])
    pretty(
        "dispatch",
        client.post(
            "/v1/dispatch/task",
            json={
                "title": "Inspect codex-bridge health",
                "input_kind": "task",
                "context": "Check service status and router health only with safe commands",
                "repo": "codex-bridge",
                "source": "smoke",
                "constraints": ["Safe commands only"],
            },
        ).json(),
    )


if __name__ == "__main__":
    main()
