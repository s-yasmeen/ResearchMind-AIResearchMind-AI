from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ============================================================
# PROJECT ROOT / ENVIRONMENT
# ============================================================

CORE_DIR = Path(__file__).resolve().parent
ROOT_DIR = CORE_DIR.parent
ENV_FILE = ROOT_DIR / ".env"

try:
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)

except Exception as exc:
    print(f"Warning: could not load .env: {exc}")


# ============================================================
# LANGCHAIN OPENAI
# ============================================================

try:
    from langchain_openai import ChatOpenAI

except Exception:
    ChatOpenAI = None


# ============================================================
# CUSTOM ERRORS
# ============================================================


class DailyRateLimitError(RuntimeError):
    """
    Raised when OpenRouter reports that the daily
    free-model quota has been exhausted.

    This error is NOT retryable.
    """

    retryable = False

    def __init__(
        self,
        message: str,
        reset_time: str | None = None,
    ):
        super().__init__(message)
        self.reset_time = reset_time


class AuthenticationLLMError(RuntimeError):
    """
    Raised when the OpenRouter API key is rejected.
    """

    retryable = False


class TemporaryLLMError(RuntimeError):
    """
    Temporary provider/network failure.
    """

    retryable = True


# ============================================================
# ERROR HELPERS
# ============================================================


def error_text(error: BaseException) -> str:
    return str(error).lower()


def is_daily_rate_limit(
    error: BaseException,
) -> bool:

    text = error_text(error)

    indicators = (
        "free-models-per-day",
        "openrouter_free_tier_daily",
        "daily free-model",
        "daily free model",
        "daily quota",
        "free model quota",
        "daily limit",
    )

    return any(
        indicator in text
        for indicator in indicators
    )


def is_authentication_error(
    error: BaseException,
) -> bool:

    text = error_text(error)

    return any(
        marker in text
        for marker in (
            "401",
            "unauthorized",
            "authentication",
            "missing authentication header",
            "invalid api key",
            "invalid_api_key",
            "user not found",
        )
    )


def is_temporary_rate_limit(
    error: BaseException,
) -> bool:

    # IMPORTANT:
    # Daily quota exhaustion is permanent for this
    # execution and must NEVER be retried.
    if is_daily_rate_limit(error):
        return False

    text = error_text(error)

    # A normal HTTP 429 may be temporary.
    if "429" in text:
        return True

    temporary_markers = (
        "upstream_provider_shared_pool",
        "temporarily rate-limited",
        "provider returned error",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
    )

    return any(
        marker in text
        for marker in temporary_markers
    )


def is_retryable_provider_error(
    error: BaseException,
) -> bool:

    if is_daily_rate_limit(error):
        return False

    if is_authentication_error(error):
        return False

    text = error_text(error)

    # Temporary HTTP errors.
    for code in (
        "408",
        "409",
        "425",
        "429",
        "500",
        "502",
        "503",
        "504",
    ):
        if code in text:
            return True

    # Temporary network/provider failures.
    for phrase in (
        "timeout",
        "timed out",
        "temporarily unavailable",
        "connection reset",
        "connection error",
        "temporary failure",
        "service unavailable",
        "server error",
    ):
        if phrase in text:
            return True

    return False


# ============================================================
# RATE LIMIT RESET EXTRACTION
# ============================================================


def extract_reset_time(
    error: BaseException,
) -> str | None:

    raw = str(error)

    patterns = [
        r'"X-RateLimit-Reset"\s*:\s*"?(.*?)"?[,}]',
        r"'X-RateLimit-Reset'\s*:\s*'?(.*?)'?[,}]",
        r'"x-ratelimit-reset"\s*:\s*"?(.*?)"?[,}]',
        r'"reset"\s*:\s*"?(.*?)"?[,}]',
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            raw,
            re.IGNORECASE,
        )

        if not match:
            continue

        value = match.group(1).strip()

        if not value:
            continue

        # --------------------------------------------------------
        # OpenRouter normally returns milliseconds since epoch.
        # Example:
        # 1786320000000
        # --------------------------------------------------------

        try:

            numeric = float(value)

            # Milliseconds
            if numeric > 10_000_000_000:

                dt = datetime.fromtimestamp(
                    numeric / 1000,
                    tz=timezone.utc,
                )

                return dt.isoformat()

            # Seconds
            if numeric > 1_000_000_000:

                dt = datetime.fromtimestamp(
                    numeric,
                    tz=timezone.utc,
                )

                return dt.isoformat()

        except Exception:
            pass

        return value

    return None


# ============================================================
# API KEY CLEANING
# ============================================================


def clean_api_key(
    value: str | None,
) -> str:

    key = (value or "").strip()

    # Remove accidental surrounding quotes.
    if (
        len(key) >= 2
        and key[0] in "\"'"
        and key[-1] == key[0]
    ):
        key = key[1:-1].strip()

    return key


# ============================================================
# MODEL CLEANING
# ============================================================


def clean_model_name(
    value: str | None,
) -> str:

    return (value or "").strip()


def unique_models(
    models: list[str],
) -> list[str]:

    result: list[str] = []

    for model in models:

        model = clean_model_name(model)

        if (
            model
            and model not in result
        ):
            result.append(model)

    return result


# ============================================================
# RESILIENT LLM
# ============================================================


class ResilientLLM:

    def __init__(
        self,
        clients: list,
        models: list[str],
        retries: int = 2,
        backoff: float = 3.0,
    ):

        self.clients = clients
        self.models = models

        self.retries = max(
            1,
            retries,
        )

        self.backoff = max(
            0.5,
            backoff,
        )

        self.current_index = 0

        self.disabled_models: set[str] = set()

        self.last_error: Exception | None = None

        self.last_reset_time: str | None = None


    # ========================================================
    # INVOKE
    # ========================================================


    def invoke(
        self,
        prompt: str,
        **kwargs: Any,
    ):

        if not self.clients:

            raise RuntimeError(
                "No LLM clients configured."
            )

        last_error: Exception | None = None

        attempted_models = 0

        for index, client in enumerate(
            self.clients
        ):

            model = self.models[index]

            # ------------------------------------------------
            # Skip permanently disabled models.
            # ------------------------------------------------

            if model in self.disabled_models:

                print(
                    f"Skipping disabled model: {model}"
                )

                continue

            attempted_models += 1

            print()
            print(
                f"LLM model: {model}"
            )

            for attempt in range(
                1,
                self.retries + 1,
            ):

                try:

                    response = client.invoke(
                        prompt,
                        **kwargs,
                    )

                    self.current_index = index

                    self.last_error = None

                    return response

                except Exception as exc:

                    last_error = exc

                    self.last_error = exc

                    print(
                        f"LLM attempt "
                        f"{attempt}/{self.retries} "
                        f"failed: {exc}"
                    )


                    # ========================================
                    # DAILY OPENROUTER QUOTA
                    # ========================================

                    if is_daily_rate_limit(exc):

                        reset = extract_reset_time(
                            exc
                        )

                        self.last_reset_time = reset

                        print()
                        print(
                            "OpenRouter daily free-model "
                            "quota exhausted."
                        )

                        if reset:

                            print(
                                f"Rate-limit reset: {reset}"
                            )

                        print(
                            "No additional retry will be attempted."
                        )

                        # CRITICAL:
                        #
                        # Do NOT:
                        # - retry the same request
                        # - retry the same model
                        # - rotate through other :free models
                        #
                        raise DailyRateLimitError(
                            "OpenRouter daily free-model "
                            "quota is exhausted. "
                            "Do not retry repeatedly.",
                            reset_time=reset,
                        ) from exc


                    # ========================================
                    # AUTHENTICATION
                    # ========================================

                    if is_authentication_error(exc):

                        print()
                        print(
                            f"Authentication error "
                            f"for model: {model}"
                        )

                        self.disabled_models.add(
                            model
                        )

                        print(
                            "Switching to next configured model..."
                        )

                        break


                    # ========================================
                    # TEMPORARY PROVIDER ERROR
                    # ========================================

                    if (
                        attempt < self.retries
                        and is_retryable_provider_error(
                            exc
                        )
                    ):

                        wait = (
                            self.backoff
                            * (
                                2
                                ** (
                                    attempt - 1
                                )
                            )
                        )

                        wait = min(
                            wait,
                            30,
                        )

                        print(
                            "Temporary provider error."
                        )

                        print(
                            f"Waiting {wait:.1f}s..."
                        )

                        time.sleep(
                            wait
                        )

                        continue


                    # No retry.
                    break

            print(
                f"Model exhausted: {model}"
            )


        # ====================================================
        # ALL MODELS FAILED
        # ====================================================

        disabled = ", ".join(
            sorted(
                self.disabled_models
            )
        )

        message = (
            "All configured LLM models failed. "
            f"Models attempted: {attempted_models}. "
            f"Disabled models: "
            f"{disabled or 'none'}. "
            f"Last error: {last_error}"
        )

        raise RuntimeError(
            message
        ) from last_error


# ============================================================
# LLM FACTORY
# ============================================================


class LLMFactory:

    _instance = None


    # ========================================================
    # PUBLIC
    # ========================================================


    @classmethod
    def get_llm(cls):

        if cls._instance is None:

            cls._instance = (
                cls._build()
            )

        return cls._instance


    # ========================================================
    # RESET SINGLETON
    # ========================================================


    @classmethod
    def reset(cls):

        cls._instance = None


    # ========================================================
    # BUILD
    # ========================================================


    @classmethod
    def _build(cls):

        if ChatOpenAI is None:

            raise RuntimeError(
                "langchain-openai is not installed.\n\n"
                "Run:\n"
                "pip install -U langchain-openai"
            )


        # ====================================================
        # API KEY
        # ====================================================

        api_key = clean_api_key(
            os.getenv(
                "OPENROUTER_API_KEY",
                "",
            )
        )

        if not api_key:

            raise RuntimeError(
                "OPENROUTER_API_KEY is missing.\n\n"
                f"Expected .env file:\n"
                f"{ENV_FILE}\n\n"
                "Example:\n"
                "OPENROUTER_API_KEY=sk-or-v1-..."
            )


        # ====================================================
        # PRIMARY MODEL
        # ====================================================

        primary = clean_model_name(
            os.getenv(
                "OPENROUTER_MODEL",
                "inclusionai/ling-3.0-tiny:free",
            )
        )


        # ====================================================
        # FALLBACK MODELS
        # ====================================================

        fallback_text = os.getenv(
            "OPENROUTER_FALLBACK_MODELS",
            "",
        ).strip()

        fallback_models = [
            clean_model_name(model)
            for model in fallback_text.split(",")
            if clean_model_name(model)
        ]


        # ====================================================
        # MODEL LIST
        # ====================================================

        models = unique_models(
            [
                primary,
                *fallback_models,
            ]
        )

        if not models:

            raise RuntimeError(
                "No OpenRouter models configured.\n\n"
                "Set OPENROUTER_MODEL or "
                "OPENROUTER_FALLBACK_MODELS."
            )


        # ====================================================
        # OPENROUTER BASE URL
        # ====================================================

        base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        ).strip()

        # Remove accidental trailing slash.
        base_url = base_url.rstrip("/")


        # ====================================================
        # PARAMETERS
        # ====================================================

        try:

            temperature = float(
                os.getenv(
                    "OPENROUTER_TEMPERATURE",
                    "0.2",
                )
            )

        except ValueError:

            temperature = 0.2


        try:

            timeout = float(
                os.getenv(
                    "OPENROUTER_TIMEOUT",
                    "90",
                )
            )

        except ValueError:

            timeout = 90.0


        try:

            retries = int(
                os.getenv(
                    "RESEARCHMIND_LLM_RETRIES",
                    "2",
                )
            )

        except ValueError:

            retries = 2


        try:

            backoff = float(
                os.getenv(
                    "RESEARCHMIND_LLM_BACKOFF",
                    "3",
                )
            )

        except ValueError:

            backoff = 3.0


        # ====================================================
        # BUILD CLIENTS
        # ====================================================

        clients = []

        for model in models:

            print()
            print("=" * 60)
            print(
                "Provider : OpenRouter"
            )
            print(
                f"Model    : {model}"
            )
            print(
                "Key Found: True"
            )
            print(
                f"Key Prefix: {api_key[:8]}..."
            )
            print(
                f"Base URL : {base_url}"
            )
            print("=" * 60)


            client = ChatOpenAI(

                api_key=api_key,

                base_url=base_url,

                model=model,

                temperature=temperature,

                timeout=timeout,

                # ResearchMind handles retries itself.
                max_retries=0,

                default_headers={
                    "Authorization":
                        f"Bearer {api_key}",

                    "HTTP-Referer":
                        "http://localhost",

                    "X-Title":
                        "ResearchMind-AI",
                },
            )

            clients.append(
                client
            )


        # ====================================================
        # RETURN RESILIENT WRAPPER
        # ====================================================

        return ResilientLLM(

            clients=clients,

            models=models,

            retries=retries,

            backoff=backoff,
        )


# ============================================================
# OPTIONAL DIRECT TEST
# ============================================================


if __name__ == "__main__":

    print()
    print(
        "Testing ResearchMind LLM Factory..."
    )

    try:

        llm = LLMFactory.get_llm()

        print()
        print(
            "LLM Factory initialized successfully."
        )

        print(
            "Models:"
        )

        for model in llm.models:

            print(
                f"  - {model}"
            )

    except Exception as exc:

        print()
        print(
            "LLM Factory initialization failed:"
        )

        print(
            exc
        )