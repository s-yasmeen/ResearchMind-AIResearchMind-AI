import unittest

from engine.task_registry import TASK_IDS
from run_researchmind import (
    EXPECTED_TASK_IDS,
    task_counts,
    task_not_implemented_count,
)


class RunnerReportingTests(unittest.TestCase):
    def test_runner_uses_canonical_task_registry(self):
        self.assertEqual(tuple(EXPECTED_TASK_IDS), TASK_IDS)

    def test_not_implemented_tasks_are_not_reported_as_pending(self):
        tasks = [
            {"task_id": "P1-T1", "status": "completed"},
            {"task_id": "P1-T2", "status": "failed"},
            {"task_id": "P1-T3", "status": "pending"},
            {"task_id": "P1-T4", "status": "running"},
        ]
        tasks.extend(
            {"task_id": task_id, "status": "not_implemented"}
            for task_id in TASK_IDS[4:]
        )

        self.assertEqual(task_counts(tasks), (1, 1, 2))
        self.assertEqual(task_not_implemented_count(tasks), 22)


if __name__ == "__main__":
    unittest.main()
