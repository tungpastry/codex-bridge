from __future__ import annotations

from typing import Iterable

from app.schemas.decision_trace import ConfidenceLevel, DecisionTrace, MatchedRule


def matched_rule(
    *,
    rule_name: str,
    rule_type: str,
    matched_value: str,
    effect: str,
    note: str = "",
) -> MatchedRule:
    return MatchedRule(
        rule_name=rule_name,
        rule_type=rule_type,
        matched_value=matched_value,
        effect=effect,
        note=note,
    )


def confidence_from_matches(matches: Iterable[MatchedRule], *, risky: bool = False, strong: bool = False) -> ConfidenceLevel:
    items = list(matches)
    if risky or strong or len(items) >= 4:
        return "high"
    if len(items) >= 2:
        return "medium"
    return "low"


def build_decision_trace(matches: list[MatchedRule], *, risky: bool = False, strong: bool = False) -> DecisionTrace:
    return DecisionTrace(
        matched_rules=matches,
        confidence=confidence_from_matches(matches, risky=risky, strong=strong),
    )
