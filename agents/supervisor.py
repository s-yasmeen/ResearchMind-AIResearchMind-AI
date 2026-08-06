from core.llm_factory import LLMFactory

from agents.literature_agent import LiteratureAgent
from agents.methodology_agent import MethodologyAgent
from agents.writing_agent import WritingAgent


class Supervisor:

    def __init__(self):

        self.llm = LLMFactory.get_llm()

        self.literature = LiteratureAgent()
        self.methodology = MethodologyAgent()
        self.writing = WritingAgent()

    def process(self, query: str):

        router_prompt = f"""
You are the supervisor of ResearchMind.

Available agents:

Literature
Methodology
Writing

Return ONLY one word.

User:
{query}
"""

        selected = self.llm.invoke(router_prompt).content.strip()

        print(f"\nSupervisor selected: {selected}")

        if selected == "Literature":
            return self.literature.run(query)

        elif selected == "Methodology":
            return self.methodology.run(query)

        elif selected == "Writing":
            return self.writing.run(query)

        else:
            return f"Unknown agent: {selected}"