from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Optional


PATH_PATTERN = re.compile(
    r"(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:go|py|ts|tsx|js|jsx|json|ya?ml|toml|md|sql|sh|service)"
)


def fold_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", (text or "").strip())
    return collapsed.lower()


def normalize_search_text(text: str) -> str:
    return normalize_text(fold_accents(text))


def split_lines(text: str) -> List[str]:
    return [line.rstrip() for line in (text or "").splitlines() if line.strip()]


def detect_language(text: str) -> str:
    raw = text or ""
    lowered = normalize_search_text(raw)
    vietnamese_markers = [
        " loi ",
        "loi",
        "that bai",
        "ngoai le",
        "trien khai",
        "nhat ky",
        "dich vu",
        "bo nho",
        "o dia",
        "khoi dong lai",
    ]
    if any(marker in f" {lowered} " for marker in vietnamese_markers):
        return "vi"
    if re.search(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", raw.lower()):
        return "vi"
    return "en"


def first_sentence(text: str, limit: int = 220) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if not compact:
        return ""
    match = re.split(r"(?<=[.!?])\s+", compact, maxsplit=1)
    sentence = match[0]
    return sentence[: limit - 3] + "..." if len(sentence) > limit else sentence


def summarize_block(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def extract_path_tokens(text: str, limit: int = 8) -> List[str]:
    matches = PATH_PATTERN.findall(text or "")
    seen = []
    for item in matches:
        if item not in seen:
            seen.append(item)
        if len(seen) >= limit:
            break
    return seen


def unique_list(items: Iterable[str], limit: Optional[int] = None) -> List[str]:
    seen = []
    for item in items:
        cleaned = (item or "").strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
        if limit is not None and len(seen) >= limit:
            break
    return seen


def pick_matching_lines(text: str, keywords: Iterable[str], limit: int = 6) -> List[str]:
    normalized_keywords = [normalize_search_text(keyword) for keyword in keywords]
    selected: List[str] = []
    for line in split_lines(text):
        haystack = normalize_search_text(line)
        if any(keyword in haystack for keyword in normalized_keywords):
            selected.append(line)
        if len(selected) >= limit:
            break
    return selected
