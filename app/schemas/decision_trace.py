from __future__ import annotations

from typing import List, Literal

from pydantic import Field

from app.schemas.common import SchemaBase


ConfidenceLevel = Literal["low", "medium", "high"]


class MatchedRule(SchemaBase):
    rule_name: str
    rule_type: str
    matched_value: str = ""
    effect: str
    note: str = ""


class DecisionTrace(SchemaBase):
    matched_rules: List[MatchedRule] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
