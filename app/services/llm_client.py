from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class LLMClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate_text(self, prompt: str, format_json: bool = False) -> Optional[str]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        if format_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post("{0}/api/generate".format(self.base_url), json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        text = data.get("response")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return None
