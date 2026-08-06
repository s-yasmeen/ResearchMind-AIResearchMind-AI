from core.llm_factory import LLMFactory
from core.retriever import Retriever


class LiteratureAgent:

    def __init__(self):
        self.llm = LLMFactory.get_llm()

    def run(self, query):

        print("\nSearching knowledge base...")

        docs = Retriever.retrieve(query, k=8)

        if not docs:
            return (
                "No relevant papers were found in the vector database.\n"
                "Run the paper indexer first."
            )

        context = "\n\n".join(docs)

        prompt = f"""
You are ResearchMind, an expert IEEE research assistant.

Use ONLY the supplied context.

If the answer is not supported by the context,
state that additional papers are required.

Research Question:
{query}

Context:
{context}

Write a detailed literature review with the following sections:

1. Overview
2. Current State of the Art
3. Common Techniques
4. Datasets Used
5. Evaluation Metrics
6. Research Gaps
7. Future Research Directions

Requirements:

- Be technically accurate.
- Do not invent information.
- Base every statement on the supplied context.
- Write in professional IEEE style.
- Produce around 800–1200 words.
"""

        response = self.llm.invoke(prompt)

        return response.content