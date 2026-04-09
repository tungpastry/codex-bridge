from app.policy.diff_policy import summarize_diff_policy
from app.schemas.diff_summary import DiffSummaryRequest, DiffSummaryResponse


def summarize_diff(request: DiffSummaryRequest) -> DiffSummaryResponse:
    return summarize_diff_policy(request)
