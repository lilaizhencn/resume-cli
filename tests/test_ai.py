from __future__ import annotations

from types import SimpleNamespace

import pytest

from resume_cli.ai import OpenAIClient
from resume_cli.errors import AIResponseError
from resume_cli.schemas import ResumeInfo


def test_invalid_provider_json_is_rejected() -> None:
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(
                    content="not-json",
                    parsed=None,
                    refusal=None,
                ),
            )
        ]
    )

    with pytest.raises(AIResponseError, match="required schema"):
        OpenAIClient._validate_completion(completion, ResumeInfo)


def test_incomplete_provider_response_is_rejected() -> None:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(finish_reason="length", message=SimpleNamespace())]
    )

    with pytest.raises(AIResponseError, match="incomplete"):
        OpenAIClient._validate_completion(completion, ResumeInfo)
