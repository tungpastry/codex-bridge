from app.policy.task_policy import classify_task_policy
from app.schemas.task import TaskClassificationRequest, TaskClassificationResponse


def classify_task(request: TaskClassificationRequest) -> TaskClassificationResponse:
    return classify_task_policy(request)
