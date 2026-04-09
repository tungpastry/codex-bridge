from __future__ import annotations

import re
from typing import List

from app.policy.decision_trace import build_decision_trace, matched_rule
from app.schemas.diff_summary import DiffSummaryRequest, DiffSummaryResponse
from app.utils.text import first_sentence, normalize_search_text, unique_list


def _changed_files(diff_text: str) -> List[str]:
    files = re.findall(r"^\+\+\+ b/(.+)$", diff_text, flags=re.MULTILINE)
    if not files:
        files = re.findall(r"^diff --git a/(.+?) b/(.+)$", diff_text, flags=re.MULTILINE)
        files = [item[0] for item in files]
    return unique_list(files, limit=12)


def summarize_diff_policy(request: DiffSummaryRequest) -> DiffSummaryResponse:
    diff_text = request.diff_text or ""
    changed_files = _changed_files(diff_text)
    haystack = normalize_search_text(diff_text + " " + " ".join(changed_files))

    flags: List[str] = []
    matches = []
    if any(token in haystack for token in ("config", ".env", ".toml", ".yaml", ".yml", "settings", "compose")):
        flags.append("config")
        matches.append(matched_rule(rule_name="config_flag", rule_type="risk", matched_value="config", effect="risk:config"))
    if any(token in haystack for token in ("auth", "oauth", "token", "session", "password")):
        flags.append("auth")
        matches.append(matched_rule(rule_name="auth_flag", rule_type="risk", matched_value="auth", effect="risk:auth"))
    if any(token in haystack for token in ("database", "postgres", "prisma", "sqlalchemy", ".sql", "schema.prisma")):
        flags.append("database")
        matches.append(matched_rule(rule_name="database_flag", rule_type="risk", matched_value="database", effect="risk:database"))
    if any(token in haystack for token in ("migration", "alembic", "migrations/", "schema change")):
        flags.append("migration")
        matches.append(matched_rule(rule_name="migration_flag", rule_type="risk", matched_value="migration", effect="risk:migration"))
    if any(token in haystack for token in ("secret", "permission", "firewall", "security", "credential")):
        flags.append("security")
        matches.append(matched_rule(rule_name="security_flag", rule_type="risk", matched_value="security", effect="risk:security"))

    risk_level = "low"
    if "security" in flags or "migration" in flags:
        risk_level = "high"
    elif any(flag in flags for flag in ("auth", "database", "config")):
        risk_level = "medium"

    review_focus: List[str] = []
    if "config" in flags:
        review_focus.append("Verify config defaults, env names, and rollback behavior.")
    if "auth" in flags:
        review_focus.append("Review auth/session/token handling and any privilege changes.")
    if "database" in flags:
        review_focus.append("Check data compatibility, migrations, and production safety.")
    if "migration" in flags:
        review_focus.append("Confirm migration ordering, rollback path, and production impact.")
    if "security" in flags:
        review_focus.append("Audit secret handling, permissions, and exposure risks.")
    if not review_focus:
        review_focus.append("Validate changed code paths, tests, and user-facing behavior.")

    if risk_level == "high":
        recommended_tool = "human"
        next_step = "Run human review before any deploy or destructive action."
    elif any(path.endswith((".go", ".py", ".ts", ".tsx", ".js")) for path in changed_files):
        recommended_tool = "codex"
        next_step = "Use Codex for implementation-aware review and follow-up fixes."
    else:
        recommended_tool = "gemini"
        next_step = "Use Gemini for ops-focused diff triage and rollout checklist."

    matches.append(
        matched_rule(
            rule_name="diff_route_selected",
            rule_type="decision",
            matched_value=recommended_tool,
            effect=f"route:{recommended_tool}",
        )
    )
    matches.append(
        matched_rule(
            rule_name="diff_risk_level_selected",
            rule_type="decision",
            matched_value=risk_level,
            effect=f"risk:{risk_level}",
        )
    )

    summary = "Changed {0} file(s) in {1}: {2}".format(
        len(changed_files),
        request.repo,
        ", ".join(changed_files[:4]) if changed_files else "no filenames detected",
    )
    return DiffSummaryResponse(
        summary=first_sentence(summary, limit=220),
        risk_level=risk_level,
        risk_flags=unique_list(flags, limit=5),
        review_focus=unique_list(review_focus, limit=5),
        recommended_tool=recommended_tool,
        next_step=next_step,
        decision_trace=build_decision_trace(matches, risky=risk_level == "high", strong=risk_level != "low"),
    )
