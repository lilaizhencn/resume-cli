from __future__ import annotations

from pathlib import Path

import pytest

from resume_cli.ai import MockAIClient
from resume_cli.errors import InputError
from resume_cli.pdf_parser import PDFParser
from resume_cli.services import (
    ResumeService,
    jd_has_education_requirement,
    redact_direct_identifiers,
)


def test_mock_score_needs_no_api_key(make_text_pdf, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pdf_path = make_text_pdf("Synthetic Candidate\nPython TypeScript Docker project experience")
    jd_path = tmp_path / "jd.txt"
    jd_path.write_text(
        "Looking for a Python full-stack engineer. Bachelor degree required.",
        encoding="utf-8",
    )
    service = ResumeService(PDFParser(), MockAIClient)

    result = service.score(pdf_path, jd_path)

    assert result.overall_score == 82
    assert result.skill_score == 88


def test_missing_education_requirement_is_neutral(make_text_pdf, tmp_path: Path) -> None:
    pdf_path = make_text_pdf("Synthetic Candidate\nPython TypeScript Docker project experience")
    jd_path = tmp_path / "jd-without-education.txt"
    jd_path.write_text("Looking for a Python full-stack engineer.", encoding="utf-8")
    service = ResumeService(PDFParser(), MockAIClient)

    result = service.score(pdf_path, jd_path)

    assert not jd_has_education_requirement(jd_path.read_text(encoding="utf-8"))
    assert result.education_score == 100
    assert result.overall_score == 87


def test_empty_and_missing_jd_are_reported(make_text_pdf, tmp_path: Path) -> None:
    pdf_path = make_text_pdf("Synthetic resume with enough embedded text")
    service = ResumeService(PDFParser(), MockAIClient)

    with pytest.raises(InputError, match="does not exist"):
        service.score(pdf_path, tmp_path / "missing.txt")

    empty_jd = tmp_path / "empty.txt"
    empty_jd.write_text("   ", encoding="utf-8")
    with pytest.raises(InputError, match="empty"):
        service.score(pdf_path, empty_jd)


def test_direct_identifiers_are_redacted_before_scoring() -> None:
    text = "姓名：李明\nEmail: liming@example.com\nPhone: 13800138000\n2018 - 2024"

    redacted = redact_direct_identifiers(text)

    assert "李明" not in redacted
    assert "liming@example.com" not in redacted
    assert "13800138000" not in redacted
    assert "2018 - 2024" in redacted


def test_detects_chinese_and_english_education_requirements() -> None:
    assert jd_has_education_requirement("本科及以上学历")
    assert jd_has_education_requirement("Bachelor degree required")
    assert not jd_has_education_requirement("Python and Docker experience")
