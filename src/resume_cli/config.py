"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from resume_cli.errors import ConfigurationError

DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 60.0
MAX_RESUME_CHARS = 120_000
MAX_JD_CHARS = 60_000


@dataclass(frozen=True, slots=True)
class AISettings:
    """Settings required by the real OpenAI client."""

    api_key: str
    model: str
    timeout_seconds: float = DEFAULT_OPENAI_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> AISettings:
        """Load a local .env without overriding the process environment."""

        load_dotenv(override=False)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()

        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Set it in the environment or use --mock."
            )
        if not model:
            raise ConfigurationError("OPENAI_MODEL must not be empty.")

        return cls(api_key=api_key, model=model)
