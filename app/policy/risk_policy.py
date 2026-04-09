from __future__ import annotations

from app.policy.decision_trace import matched_rule
from app.schemas.decision_trace import MatchedRule
from app.utils.text import normalize_search_text


RISKY_KEYWORDS = (
    "drop table",
    "delete production data",
    "rotate secret",
    "auth change",
    "firewall",
    "schema migration in production",
    "xoa du lieu production",
    "doi secret",
    "doi auth",
    "migration schema production",
)


def match_risk_rules(text: str) -> list[MatchedRule]:
    haystack = normalize_search_text(text)
    matches = [
        matched_rule(
            rule_name="risky_signal_detected",
            rule_type="risk",
            matched_value=keyword,
            effect="route:human",
        )
        for keyword in RISKY_KEYWORDS
        if normalize_search_text(keyword) in haystack
    ]
    deduped: list[MatchedRule] = []
    seen: set[tuple[str, str, str, str]] = set()
    for match in matches:
        key = (match.rule_name, match.rule_type, match.matched_value, match.effect)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(match)
        if len(deduped) >= 8:
            break
    return deduped


def contains_risky_signal(text: str) -> bool:
    haystack = normalize_search_text(text)
    return any(normalize_search_text(keyword) in haystack for keyword in RISKY_KEYWORDS)
