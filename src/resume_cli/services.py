"""Synchronous application use cases."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from resume_cli.ai import AIClient
from resume_cli.config import MAX_JD_CHARS, MAX_RESUME_CHARS
from resume_cli.errors import InputError
from resume_cli.pdf_parser import PDFParser
from resume_cli.schemas import ResumeInfo, ScoreResult, build_score_result

EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
CHINESE_MOBILE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
GROUPED_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[-. ]?)?(?:\(?\d{2,4}\)?[-. ]?)\d{3,4}[-. ]\d{4}(?!\d)"
)
LABELED_NAME_RE = re.compile(r"(?im)^(?:姓名|name)\s*[:：]\s*[^\n]{1,40}$")
EDUCATION_REQUIREMENT_RE = re.compile(
    r"学历|学位|本科|大专|硕士|博士|教育背景|专业要求|"
    r"\b(?:education|degree|bachelor|master|ph\.?d|college|university)\b",
    re.IGNORECASE,
)


class ResumeService:
    def __init__(
        self,
        parser: PDFParser,
        ai_client_factory: Callable[[], AIClient] | None = None,
    ) -> None:
        self._parser = parser
        self._ai_client_factory = ai_client_factory

    def parse(self, pdf_path: Path) -> str:
        return self._parser.parse(pdf_path)

    def extract(self, pdf_path: Path) -> ResumeInfo:
        resume_text = self._parser.parse(pdf_path)
        self._check_length("Resume", resume_text, MAX_RESUME_CHARS)
        return self._client().extract_resume(resume_text)

    def score(self, pdf_path: Path, jd_path: Path) -> ScoreResult:
        resume_text = self._parser.parse(pdf_path)
        jd_text = self._read_jd(jd_path)
        self._check_length("Resume", resume_text, MAX_RESUME_CHARS)
        self._check_length("JD", jd_text, MAX_JD_CHARS)

        redacted_resume = redact_direct_identifiers(resume_text)
        draft = self._client().score_resume(redacted_resume, jd_text)
        if not jd_has_education_requirement(jd_text):
            draft = draft.model_copy(update={"education_score": 100})
        return build_score_result(draft)

    def _client(self) -> AIClient:
        if self._ai_client_factory is None:
            raise RuntimeError("AI client is not configured for this service")
        return self._ai_client_factory()

    @staticmethod
    def _read_jd(jd_path: Path) -> str:
        path = jd_path.expanduser()
        if not path.exists():
            raise InputError(f"JD file does not exist: {path}")
        if not path.is_file():
            raise InputError(f"JD path is not a regular file: {path}")
        try:
            content = path.read_text(encoding="utf-8-sig").strip()
        except UnicodeDecodeError as error:
            raise InputError("JD file must be UTF-8 encoded text.") from error
        except OSError as error:
            raise InputError(f"JD file cannot be read: {path}") from error
        if not content:
            raise InputError("JD file is empty.")
        return content

    @staticmethod
    def _check_length(label: str, text: str, limit: int) -> None:
        if len(text) > limit:
            raise InputError(
                f"{label} text is too large ({len(text)} characters; maximum is {limit})."
            )


def redact_direct_identifiers(text: str) -> str:
    """Remove common direct identifiers before a scoring request."""

    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = CHINESE_MOBILE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = GROUPED_PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return LABELED_NAME_RE.sub("Name: [REDACTED_NAME]", redacted)


def jd_has_education_requirement(jd_text: str) -> bool:
    """Return whether a JD explicitly mentions an education-related criterion."""

    return EDUCATION_REQUIREMENT_RE.search(jd_text) is not None
