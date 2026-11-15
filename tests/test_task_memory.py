import tempfile
import unittest
from pathlib import Path

from core.task_memory import TaskMemory


class TaskMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory_root = Path(self.temp_dir.name) / "memory"
        self.memory = TaskMemory(root=self.memory_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_checkpoint_round_trip_preserves_completed_task(self):
        self.memory.initialize("climate risk forecasting")
        self.memory.save(
            result={
                "task_id": "P1-T1",
                "status": "completed",
                "output": "Evidence-backed review",
            }
        )

        restored = TaskMemory(root=self.memory_root)
        checkpoint = restored.load("climate risk forecasting")

        self.assertIsNotNone(checkpoint)
        self.assertEqual(
            restored.get_result("P1-T1")["output"],
            "Evidence-backed review",
        )
        self.assertEqual(restored.get_completed_ids(), {"P1-T1"})

    def test_completed_task_cannot_be_downgraded_to_pending(self):
        self.memory.initialize("robust anomaly detection")
        self.memory.save(
            result={
                "task_id": "P1-T1",
                "status": "completed",
                "output": "Completed result",
            }
        )

        self.memory.mark_pending("P1-T1", "retry requested")

        saved = self.memory.get_result("P1-T1")
        self.assertEqual(saved["status"], "completed")
        self.assertEqual(saved["output"], "Completed result")

    def test_quota_exhaustion_keeps_task_resumable(self):
        self.memory.initialize("medical image segmentation")
        self.memory.mark_quota_exhausted(
            task_id="P1-T2",
            reason="Daily provider quota exhausted",
            reset_time="2026-11-16T00:00:00+00:00",
        )

        restored = TaskMemory(root=self.memory_root)
        restored.load("medical image segmentation")

        self.assertTrue(restored.quota_blocked)
        self.assertEqual(
            restored.get_result("P1-T2")["status"],
            "pending",
        )
        self.assertEqual(
            restored.quota_reset_time,
            "2026-11-16T00:00:00+00:00",
        )

    def test_checkpoint_does_not_mix_different_queries(self):
        self.memory.initialize("query one")
        self.memory.save(
            result={
                "task_id": "P1-T1",
                "status": "completed",
            }
        )

        restored = TaskMemory(root=self.memory_root)
        checkpoint = restored.load("query two")

        self.assertIsNone(checkpoint)
        self.assertIsNone(restored.query)
        self.assertEqual(restored.get_results(), [])

    def test_duplicate_task_records_keep_latest_state(self):
        self.memory.initialize("duplicate task test")
        self.memory.save(
            results=[
                {"task_id": "P1-T1", "status": "running"},
                {"task_id": "P1-T1", "status": "completed", "output": "final"},
            ]
        )

        self.assertEqual(len(self.memory.get_results()), 1)
        self.assertEqual(
            self.memory.get_result("P1-T1")["status"],
            "completed",
        )


if __name__ == "__main__":
    unittest.main()
