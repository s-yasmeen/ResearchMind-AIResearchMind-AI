import unittest

from engine.task_registry import (
    TASK_IDS,
    TASK_REGISTRY,
    dependencies_satisfied,
    validate_registry,
)


class TaskRegistryTests(unittest.TestCase):
    def test_registry_contains_exactly_26_unique_tasks(self):
        self.assertEqual(len(TASK_IDS), 26)
        self.assertEqual(len(set(TASK_IDS)), 26)
        self.assertEqual(TASK_IDS[0], "P1-T1")
        self.assertEqual(TASK_IDS[-1], "P5-T6")

    def test_registry_dependencies_are_valid(self):
        validate_registry()
        self.assertEqual(TASK_REGISTRY[0].dependencies, ())
        self.assertEqual(TASK_REGISTRY[1].dependencies, ("P1-T1",))

    def test_task_is_blocked_until_prerequisite_is_complete(self):
        self.assertFalse(dependencies_satisfied("P1-T2", set()))
        self.assertTrue(dependencies_satisfied("P1-T2", {"P1-T1"}))

    def test_later_phase_requires_prior_workflow_chain(self):
        self.assertFalse(dependencies_satisfied("P5-T6", {"P5-T5"}))
        self.assertTrue(dependencies_satisfied(
            "P5-T6", {task_id for task_id in TASK_IDS if task_id != "P5-T6"}
        ))


if __name__ == "__main__":
    unittest.main()
