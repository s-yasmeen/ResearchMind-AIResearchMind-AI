import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agents.supervisor import Supervisor


class SupervisorRoutingTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("agents.supervisor.LLMFactory.get_llm"),
            patch("agents.supervisor.LiteratureAgent"),
            patch("agents.supervisor.MethodologyAgent"),
            patch("agents.supervisor.WritingAgent"),
        ]
        self.llm_factory, self.literature_cls, self.methodology_cls, self.writing_cls = [
            item.start() for item in self.patches
        ]
        self.addCleanup(self._stop_patches)

        self.llm = MagicMock()
        self.llm_factory.return_value = self.llm
        self.literature = self.literature_cls.return_value
        self.methodology = self.methodology_cls.return_value
        self.writing = self.writing_cls.return_value
        self.supervisor = Supervisor()

    def _stop_patches(self):
        for item in reversed(self.patches):
            item.stop()

    def test_routes_literature(self):
        self.llm.invoke.return_value = SimpleNamespace(content="Literature")
        self.literature.run.return_value = "review"
        self.assertEqual(self.supervisor.process("Compare prior work"), "review")
        self.literature.run.assert_called_once_with("Compare prior work")

    def test_routes_case_and_whitespace_variants(self):
        self.llm.invoke.return_value = SimpleNamespace(content="  methodology\n")
        self.methodology.run.return_value = "design"
        self.assertEqual(self.supervisor.process("Design an experiment"), "design")

    def test_routes_writing(self):
        self.llm.invoke.return_value = SimpleNamespace(content="Writing")
        self.writing.run.return_value = "draft"
        self.assertEqual(self.supervisor.process("Draft an abstract"), "draft")

    def test_rejects_unsupported_route(self):
        self.llm.invoke.return_value = SimpleNamespace(content="Research")
        with self.assertRaisesRegex(ValueError, "unsupported route"):
            self.supervisor.process("Investigate a topic")

    def test_rejects_empty_query_before_calling_llm(self):
        with self.assertRaises(ValueError):
            self.supervisor.process("  ")
        self.llm.invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
