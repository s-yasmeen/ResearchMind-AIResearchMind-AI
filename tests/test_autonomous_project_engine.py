import unittest

from engine.autonomous_project_engine import AutonomousProjectEngine, EXPECTED_TASK_IDS


class FakeMemory:
    def __init__(self):
        self.results = []
        self.query = None

    def load(self, query):
        self.query = query
        return {"query": query} if self.results else None

    def initialize(self, query):
        self.query = query
        self.results = []

    def get_results(self):
        return list(self.results)

    def save(self, results=None, query=None, **kwargs):
        if query is not None:
            self.query = query
        if results is not None:
            self.results = [dict(item) for item in results]


class EngineTests(unittest.TestCase):
    def test_has_all_runner_task_ids(self):
        engine = AutonomousProjectEngine(memory=FakeMemory())
        result = engine.run("test topic", max_tasks=1, resume=False)
        self.assertEqual(
            [task["task_id"] for task in result["executed_tasks"]],
            EXPECTED_TASK_IDS,
        )

    def test_executes_only_within_limit_and_marks_other_tasks_honestly(self):
        memory = FakeMemory()
        engine = AutonomousProjectEngine(memory=memory)
        engine._agent_output = lambda agent, query: "verified test output"
        result = engine.run("test topic", max_tasks=1, resume=False)

        self.assertEqual(result["counts"]["completed"], 1)
        self.assertEqual(result["executed_tasks"][0]["status"], "completed")
        self.assertEqual(result["executed_tasks"][1]["status"], "pending")
        self.assertEqual(result["executed_tasks"][3]["status"], "not_implemented")

    def test_resume_preserves_completed_tasks(self):
        memory = FakeMemory()
        memory.results = [{
            "task_id": "P1-T1",
            "title": "Evidence-grounded literature review",
            "status": "completed",
            "output": "saved output",
        }]
        engine = AutonomousProjectEngine(memory=memory)
        calls = []
        engine._agent_output = lambda agent, query: calls.append(agent) or "new output"

        result = engine.run("test topic", max_tasks=1, resume=True)
        self.assertEqual(result["executed_tasks"][0]["output"], "saved output")
        self.assertEqual(calls, ["methodology"])

    def test_rejects_empty_query(self):
        engine = AutonomousProjectEngine(memory=FakeMemory())
        with self.assertRaises(ValueError):
            engine.run("   ")


if __name__ == "__main__":
    unittest.main()
