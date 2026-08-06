from core.llm_factory import LLMFactory


class WritingAgent:

    def __init__(self):
        self.llm = LLMFactory.get_llm()

    def run(self, query):

        prompt = f"""
You are an IEEE paper writer.

Task:

{query}

Write professionally.
"""

        return self.llm.invoke(prompt).content