import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# Load .env
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_FILE, override=True)


class LLMFactory:

    @staticmethod
    def get_llm():

        provider = os.getenv("DEFAULT_PROVIDER", "openrouter").lower()

        if provider != "openrouter":
            raise ValueError(f"Unsupported provider: {provider}")

        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found")

        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

        print("=" * 60)
        print("Provider :", provider)
        print("Model    :", model)
        print("Key Found:", bool(api_key))
        print("=" * 60)

        llm = ChatOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=model,
            temperature=0.2,
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "ResearchMind-AI",
            },
        )

        return llm