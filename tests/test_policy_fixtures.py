from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.policy.diff_policy import summarize_diff_policy
from app.policy.log_policy import summarize_log_policy
from app.policy.task_policy import classify_task_policy
from app.schemas.diff_summary import DiffSummaryRequest
from app.schemas.log_summary import LogSummaryRequest
from app.schemas.task import TaskClassificationRequest


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_cases(filename: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))


class PolicyFixtureTestCase(unittest.TestCase):
    def test_task_policy_fixtures(self) -> None:
        for case in _load_cases("task_policy_cases.json"):
            with self.subTest(case=case["name"]):
                response = classify_task_policy(TaskClassificationRequest.model_validate(case["request"]))
                for key, value in case["expected"].items():
                    self.assertEqual(getattr(response, key), value)
                self.assertGreaterEqual(len(response.decision_trace.matched_rules), 1)

    def test_log_policy_fixtures(self) -> None:
        for case in _load_cases("log_policy_cases.json"):
            with self.subTest(case=case["name"]):
                response = summarize_log_policy(LogSummaryRequest.model_validate(case["request"]))
                for key, value in case["expected"].items():
                    self.assertEqual(getattr(response, key), value)
                self.assertGreaterEqual(len(response.decision_trace.matched_rules), 1)

    def test_diff_policy_fixtures(self) -> None:
        for case in _load_cases("diff_policy_cases.json"):
            with self.subTest(case=case["name"]):
                response = summarize_diff_policy(DiffSummaryRequest.model_validate(case["request"]))
                for key, value in case["expected"].items():
                    self.assertEqual(getattr(response, key), value)
                self.assertGreaterEqual(len(response.decision_trace.matched_rules), 1)
