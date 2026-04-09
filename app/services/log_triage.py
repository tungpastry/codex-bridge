from app.policy.log_policy import summarize_log_policy
from app.schemas.log_summary import LogSummaryRequest, LogSummaryResponse


def summarize_log(request: LogSummaryRequest) -> LogSummaryResponse:
    return summarize_log_policy(request)
