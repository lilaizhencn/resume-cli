from __future__ import annotations

from pathlib import Path

import pytest

from resume_cli.errors import EmptyPDFTextError, InputError, OCREmptyResultError, PDFError
from resume_cli.pdf_parser import PDFParser


class FakeOCR:
    def __init__(self, result: str = "OCR recognized resume text") -> None:
        self.result = result
        self.calls: list[tuple[Path, int]] = []

    def recognize_page(self, pdf_path: Path, page_index: int) -> str:
        self.calls.append((pdf_path, page_index))
        return self.result


def test_extracts_embedded_pdf_text_without_ocr(make_text_pdf) -> None:
    pdf_path = make_text_pdf("Alice Example\nPython TypeScript Docker")
    ocr = FakeOCR()

    result = PDFParser(ocr).parse(pdf_path)

    assert "Alice Example" in result
    assert "Python TypeScript Docker" in result
    assert ocr.calls == []


def test_automatically_uses_ocr_for_image_page(make_image_pdf) -> None:
    pdf_path = make_image_pdf()
    ocr = FakeOCR("李明\nPython 全栈工程师")

    result = PDFParser(ocr).parse(pdf_path)

    assert result == "李明\nPython 全栈工程师"
    assert ocr.calls == [(pdf_path, 0)]


def test_reports_empty_ocr_result_for_scanned_page(make_image_pdf) -> None:
    pdf_path = make_image_pdf()

    with pytest.raises(OCREmptyResultError, match="page 1"):
        PDFParser(FakeOCR("")).parse(pdf_path)


def test_rejects_missing_and_non_pdf_files(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="does not exist"):
        PDFParser().parse(tmp_path / "missing.pdf")

    text_path = tmp_path / "resume.txt"
    text_path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(InputError, match=r"Expected a \.pdf"):
        PDFParser().parse(text_path)


def test_rejects_fake_pdf_content(tmp_path: Path) -> None:
    path = tmp_path / "fake.pdf"
    path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(PDFError, match="not a valid PDF"):
        PDFParser().parse(path)


def test_reports_empty_pdf(make_text_pdf) -> None:
    path = make_text_pdf("")

    with pytest.raises(EmptyPDFTextError, match="No text"):
        PDFParser(FakeOCR("")).parse(path)
