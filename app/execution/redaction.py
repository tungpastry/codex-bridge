from __future__ import annotations

import re


SECRET_PATTERNS = (
    (
        re.compile(r"(?i)(token|secret|password)\s*[:=]\s*\S+"),
        lambda match: f"{match.group(1)}=[REDACTED]",
    ),
    (
        re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
        lambda _match: "Authorization: Bearer [REDACTED]",
    ),
)


def redact_text(text: str) -> str:
    redacted = text or ""
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def excerpt_text(text: str, *, limit: int = 2000) -> tuple[str, bool]:
    redacted = redact_text(text)
    if len(redacted) <= limit:
        return redacted, False
    return redacted[: limit - 3].rstrip() + "...", True
