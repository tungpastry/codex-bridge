from __future__ import annotations

from typing import List

from app.schemas.log_summary import LogSummaryRequest, LogSummaryResponse
from app.utils.text import first_sentence, normalize_search_text, pick_matching_lines, split_lines, summarize_block, unique_list


IMPORTANT_LINE_KEYWORDS = [
    "error",
    "failed",
    "exception",
    "traceback",
    "panic",
    "caused by",
    "timeout",
    "denied",
    "loi",
    "that bai",
    "ngoai le",
]


def summarize_log(request: LogSummaryRequest) -> LogSummaryResponse:
    lines = split_lines(request.log_text)
    important_lines = pick_matching_lines(request.log_text, IMPORTANT_LINE_KEYWORDS, limit=6)
    if not important_lines:
        important_lines = lines[-6:]

    merged = normalize_search_text(" ".join(lines[-30:]) + " " + request.context)
    needs_codex = any(token in merged for token in ("traceback", "exception", "panic", "test failed", "build failed", "validation"))
    risky = any(token in merged for token in ("firewall", "auth change", "schema migration", "drop table", "delete production data"))
    symptom = first_sentence(important_lines[0] if important_lines else request.log_text, limit=180) or "No clear symptom found."

    if risky:
        recommended_tool = "human"
        likely_cause = "The log suggests a risky or production-sensitive operation that needs human approval."
        next_step = "Pause automation and review the impact with a human operator."
    elif needs_codex:
        recommended_tool = "codex"
        likely_cause = "The log points to an application or test failure that likely needs a code change."
        next_step = "Generate a Codex brief with the failing symptom and likely files."
    else:
        recommended_tool = "gemini"
        likely_cause = "The issue looks operational and can be triaged with safe inspection commands first."
        next_step = "Run Gemini safe-ops triage and confirm service state before making changes."

    service_name = request.service or "<service>"
    recommended_commands = [
        "journalctl -u {0} -n 200 --no-pager".format(service_name),
        "systemctl status {0} --no-pager".format(service_name),
    ]
    if any(token in merged for token in ("disk", "no space", "space left", "o dia")):
        recommended_commands.append("df -h")
    if any(token in merged for token in ("memory", "oom", "bo nho")):
        recommended_commands.append("free -h")
    if any(token in merged for token in ("port", "listen", "bind")):
        recommended_commands.append("ss -ltnp")

    return LogSummaryResponse(
        symptom=symptom,
        likely_cause=likely_cause,
        important_lines=unique_list(important_lines, limit=6),
        recommended_commands=unique_list(recommended_commands, limit=6),
        needs_codex=needs_codex,
        recommended_tool=recommended_tool,
        next_step=next_step,
    )
