"""Provider-neutral AI contract plus OpenAI and deterministic mock implementations."""

from __future__ import annotations

import json
from typing import Protocol, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from resume_cli.config import AISettings
from resume_cli.errors import AIResponseError, AIServiceError
from resume_cli.prompts import EXTRACTION_SYSTEM_PROMPT, SCORING_SYSTEM_PROMPT
from resume_cli.schemas import Education, ResumeInfo, ScoreDraft

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIClient(Protocol):
    """Application-owned interface implemented by all AI providers and fakes."""

    def extract_resume(self, resume_text: str) -> ResumeInfo: ...

    def score_resume(self, resume_text: str, jd_text: str) -> ScoreDraft: ...


class OpenAIClient:
    """Synchronous OpenAI Structured Outputs adapter."""

    def __init__(self, settings: AISettings) -> None:
        self._model = settings.model
        self._client = OpenAI(
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
            max_retries=2,
        )

    @classmethod
    def from_env(cls) -> OpenAIClient:
        return cls(AISettings.from_env())

    def extract_resume(self, resume_text: str) -> ResumeInfo:
        payload = json.dumps({"resume_text": resume_text}, ensure_ascii=False)
        return self._request(EXTRACTION_SYSTEM_PROMPT, payload, ResumeInfo)

    def score_resume(self, resume_text: str, jd_text: str) -> ScoreDraft:
        payload = json.dumps(
            {"resume_text": resume_text, "jd_text": jd_text},
            ensure_ascii=False,
        )
        return self._request(SCORING_SYSTEM_PROMPT, payload, ScoreDraft)

    def _request(self, system_prompt: str, payload: str, schema: type[SchemaT]) -> SchemaT:
        try:
            completion = self._client.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": payload},
                ],
                response_format=schema,
            )
            return self._validate_completion(completion, schema)
        except AIResponseError:
            raise
        except AuthenticationError as error:
            raise AIServiceError("OpenAI authentication failed. Check OPENAI_API_KEY.") from error
        except RateLimitError as error:
            raise AIServiceError("OpenAI rate limit was reached. Wait and try again.") from error
        except APITimeoutError as error:
            raise AIServiceError("OpenAI request timed out. Try again.") from error
        except APIConnectionError as error:
            raise AIServiceError(
                "Could not connect to OpenAI. Check the network and try again."
            ) from error
        except APIStatusError as error:
            raise AIServiceError(
                f"OpenAI request failed with HTTP status {error.status_code}."
            ) from error
        except ValidationError as error:
            raise AIResponseError(
                "OpenAI returned data that did not match the required schema."
            ) from error
        except OpenAIError as error:
            raise AIServiceError("OpenAI request failed.") from error

    @staticmethod
    def _validate_completion(completion: object, schema: type[SchemaT]) -> SchemaT:
        choices = getattr(completion, "choices", None)
        if not choices:
            raise AIResponseError("OpenAI returned no completion choices.")

        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason != "stop":
            raise AIResponseError(
                f"OpenAI response was incomplete (finish reason: {finish_reason or 'unknown'})."
            )

        message = choice.message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise AIResponseError("OpenAI refused to process the supplied document.")

        content = getattr(message, "content", None)
        parsed = getattr(message, "parsed", None)
        if isinstance(content, str) and content.strip():
            try:
                return schema.model_validate_json(content)
            except ValidationError as error:
                raise AIResponseError(
                    "OpenAI returned JSON that did not match the required schema."
                ) from error

        if parsed is not None:
            try:
                return schema.model_validate(parsed)
            except ValidationError as error:
                raise AIResponseError(
                    "OpenAI returned data that did not match the required schema."
                ) from error

        raise AIResponseError("OpenAI returned an empty structured response.")


class MockAIClient:
    """Deterministic, offline results for demos and unit tests."""

    def extract_resume(self, resume_text: str) -> ResumeInfo:
        del resume_text
        return ResumeInfo(
            name="李明",
            phone="13800138000",
            email="liming@example.com",
            city="上海",
            education=[
                Education(
                    school="示例大学",
                    major="计算机科学与技术",
                    degree="本科",
                    graduation_time="2022-06",
                )
            ],
            skills=["Python", "TypeScript", "Docker", "OpenAI API"],
        )

    def score_resume(self, resume_text: str, jd_text: str) -> ScoreDraft:
        del resume_text, jd_text
        return ScoreDraft(
            skill_score=88,
            experience_score=80,
            education_score=75,
            comment=(
                "候选人具备较好的全栈开发基础，主要技能与岗位匹配，"
                "但仍需确认大模型项目的实际负责范围。"
            ),
            interview_questions=[
                "请介绍一个你主导过的全栈项目，以及你负责的关键决策。",
                "请说明你调用大模型 API 时如何处理结构化输出和失败重试。",
            ],
        )
