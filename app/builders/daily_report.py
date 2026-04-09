from __future__ import annotations

from typing import List, Tuple

from app.schemas.report import DailyReportRequest, DailyReportResponse
from app.utils.text import normalize_search_text, unique_list


DONE_PREFIXES = ("done:", "completed:", "fixed:", "xong:", "da xong:", "hoan thanh:")
OPEN_PREFIXES = ("open:", "issue:", "problem:", "mo:", "open issue:", "van de:")
NEXT_PREFIXES = ("next:", "next action:", "action:", "tiep theo:", "buoc tiep:", "ke tiep:")


def _source_items(request: DailyReportRequest) -> List[str]:
    if request.items:
        return [item.strip() for item in request.items if item.strip()]
    if request.raw_text:
        return [line.strip("- ").strip() for line in request.raw_text.splitlines() if line.strip()]
    if request.context:
        return [line.strip("- ").strip() for line in request.context.splitlines() if line.strip()]
    return []


def _bucket_for_item(item: str) -> Tuple[str, str]:
    lowered = normalize_search_text(item)
    for prefix in DONE_PREFIXES:
        if lowered.startswith(normalize_search_text(prefix)):
            return "done", item.split(":", 1)[1].strip() if ":" in item else item
    for prefix in OPEN_PREFIXES:
        if lowered.startswith(normalize_search_text(prefix)):
            return "open", item.split(":", 1)[1].strip() if ":" in item else item
    for prefix in NEXT_PREFIXES:
        if lowered.startswith(normalize_search_text(prefix)):
            return "next", item.split(":", 1)[1].strip() if ":" in item else item

    if any(token in lowered for token in ("done", "completed", "fixed", "merged", "xong", "hoan thanh")):
        return "done", item
    if any(token in lowered for token in ("next", "follow up", "todo", "tiếp", "ke tiep", "next action")):
        return "next", item
    return "open", item


def build_daily_report(request: DailyReportRequest) -> DailyReportResponse:
    done: List[str] = []
    open_issues: List[str] = []
    next_actions: List[str] = []

    for item in _source_items(request):
        bucket, value = _bucket_for_item(item)
        if bucket == "done":
            done.append(value)
        elif bucket == "next":
            next_actions.append(value)
        else:
            open_issues.append(value)

    done = unique_list(done, limit=12)
    open_issues = unique_list(open_issues, limit=12)
    next_actions = unique_list(next_actions or ["Review the open issues and choose the next safe action."], limit=12)

    lines = ["# Daily Report", "", "## Done"]
    lines.extend("- {0}".format(item) for item in (done or ["No completed items recorded."]))
    lines.extend(["", "## Open Issues"])
    lines.extend("- {0}".format(item) for item in (open_issues or ["No open issues recorded."]))
    lines.extend(["", "## Next Actions"])
    lines.extend("- {0}".format(item) for item in next_actions)

    return DailyReportResponse(
        markdown="\n".join(lines).strip() + "\n",
        done=done,
        open_issues=open_issues,
        next_actions=next_actions,
    )
