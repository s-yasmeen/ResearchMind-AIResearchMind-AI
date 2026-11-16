import sys
import types
import unittest
from unittest.mock import patch

from agents.literature_agent import LiteratureAgent


class EmptyRetriever:
    @staticmethod
    def retrieve(query, k=8):
        return []


class LiteratureEvidenceTests(unittest.TestCase):
    def test_empty_retrieval_is_not_a_successful_review(self):
        fake_module = types.ModuleType("core.retriever")
        fake_module.Retriever = EmptyRetriever
        agent = LiteratureAgent.__new__(LiteratureAgent)

        with patch.dict(sys.modules, {"core.retriever": fake_module}):
            with self.assertRaisesRegex(RuntimeError, "Index source papers"):
                agent.run("test research topic")


if __name__ == "__main__":
    unittest.main()
