from __future__ import annotations

from typing import Dict, List, Tuple

from app.schemas.task import TaskClassificationRequest, TaskClassificationResponse
from app.utils.text import extract_path_tokens, first_sentence, normalize_search_text, unique_list


KEYWORDS: Dict[str, List[str]] = {
    "bugfix": [
        "error",
        "fail",
        "failed",
        "exception",
        "traceback",
        "validation",
        "test failure",
        "panic",
        "bug",
        "loi",
        "hong",
        "that bai",
        "ngoai le",
        "traceback",
        "validate",
    ],
    "ops": [
        "deploy",
        "restart",
        "systemctl",
        "journalctl",
        "log",
        "service",
        "cron",
        "disk",
        "memory",
        "trien khai",
        "khoi dong lai",
        "nhat ky",
        "dich vu",
        "bo nho",
        "o dia",
    ],
    "risky": [
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
    ],
    "review": ["review", "diff", "patch", "pull request", "code review"],
    "setup": ["setup", "install", "bootstrap", "configure", "cai dat"],
    "research": ["research", "investigate", "analyze", "phan tich"],
    "feature": ["feature", "implement", "add", "new endpoint", "them", "xay dung"],
    "deploy": ["deploy", "release", "rollout", "production release", "trien khai"],
}


def _collect_signals(text: str) -> List[str]:
    haystack = normalize_search_text(text)
    signals = []
    for bucket in KEYWORDS.values():
        for keyword in bucket:
            if normalize_search_text(keyword) in haystack:
                signals.append(keyword)
    return unique_list(signals, limit=12)


def _pick_task_type(text: str) -> Tuple[str, List[str]]:
    haystack = normalize_search_text(text)
    matched = _collect_signals(text)
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["risky"]):
        return "unknown", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["bugfix"]):
        return "bugfix", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["deploy"]):
        return "deploy", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["ops"]):
        return "ops", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["review"]):
        return "review", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["setup"]):
        return "setup", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["research"]):
        return "research", matched
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["feature"]):
        return "feature", matched
    return "unknown", matched


def _recommended_tool(task_type: str, text: str) -> Tuple[str, str]:
    haystack = normalize_search_text(text)
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["risky"]):
        return "human", "Escalate to a human operator before any change."
    if task_type in ("ops", "deploy"):
        return "gemini", "Run Gemini auto-ops flow with the safe command subset."
    if task_type in ("bugfix", "feature", "setup"):
        return "codex", "Build a Codex brief and implement the change in the repo."
    if task_type == "review":
        return ("human", "High-risk diff needs human review.") if "security" in haystack else (
            "gemini",
            "Use Gemini for lightweight diff triage, then escalate if risk grows.",
        )
    if task_type == "research":
        return "local", "Compress the context and choose the next tool manually."
    return "local", "Keep the summary local and refine the task details."


def _severity(task_type: str, text: str) -> str:
    haystack = normalize_search_text(text)
    if any(normalize_search_text(keyword) in haystack for keyword in KEYWORDS["risky"]):
        return "critical"
    if task_type in ("deploy", "ops") and any(word in haystack for word in ("production", "prod")):
        return "high"
    if task_type == "bugfix" and any(word in haystack for word in ("panic", "traceback", "failed", "error")):
        return "high"
    if task_type in ("feature", "review", "setup"):
        return "medium"
    return "low"


def classify_task(request: TaskClassificationRequest) -> TaskClassificationResponse:
    merged = " ".join([request.title, request.context, " ".join(request.constraints)])
    task_type, signals = _pick_task_type(merged)
    recommended_tool, next_step = _recommended_tool(task_type, merged)
    return TaskClassificationResponse(
        task_type=task_type,
        severity=_severity(task_type, merged),
        repo=request.repo,
        problem_summary=first_sentence("{0}. {1}".format(request.title.strip(), request.context.strip())),
        signals=signals,
        suspected_files=extract_path_tokens(merged),
        recommended_tool=recommended_tool,
        next_step=next_step,
    )
