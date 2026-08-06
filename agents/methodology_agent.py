from core.llm_factory import LLMFactory


class MethodologyAgent:

    def __init__(self):
        self.llm = LLMFactory.get_llm()

    def run(self, query):

        prompt = f"""
You are an AI research methodology expert.

Research topic:

{query}

Recommend

- datasets
- preprocessing
- architecture
- evaluation metrics
- baselines

Explain your choices.
"""

        return self.llm.invoke(prompt).content