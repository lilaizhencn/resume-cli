"""Local PDF text extraction with page-level automatic OCR fallback."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from resume_cli.errors import EmptyPDFTextError, InputError, OCREmptyResultError, PDFError
from resume_cli.ocr import OCREngine, PaddleOCREngine

PDF_HEADER_SCAN_BYTES = 1_024
OCR_MIN_PAGE_CHARS = 16


class PDFParser:
    def __init__(self, ocr_engine: OCREngine | None = None) -> None:
        self._ocr_engine = ocr_engine

    def parse(self, pdf_path: Path) -> str:
        path = self._validate_path(pdf_path)
        reader = self._open_reader(path)
        page_texts: list[str] = []

        for page_index, page in enumerate(reader.pages):
            try:
                embedded_text = self._normalize_text(page.extract_text() or "")
            except Exception as error:
                raise PDFError(f"Could not extract text from PDF page {page_index + 1}.") from error

            meaningful_chars = self._meaningful_character_count(embedded_text)
            has_images = self._page_has_images(page)
            needs_ocr = meaningful_chars < OCR_MIN_PAGE_CHARS and has_images

            if needs_ocr:
                engine = self._ocr_engine or PaddleOCREngine()
                ocr_text = self._normalize_text(engine.recognize_page(path, page_index))
                ocr_chars = self._meaningful_character_count(ocr_text)
                if ocr_chars > meaningful_chars:
                    page_texts.append(ocr_text)
                    continue
                if not ocr_text and not embedded_text:
                    raise OCREmptyResultError(
                        f"OCR found no usable text on scanned PDF page {page_index + 1}."
                    )

            if embedded_text:
                page_texts.append(embedded_text)

        combined = "\n\n".join(page_texts).strip()
        if not combined:
            raise EmptyPDFTextError(
                "No text could be extracted from the PDF. "
                "It may be blank or the OCR result was empty."
            )
        return combined

    @staticmethod
    def _validate_path(pdf_path: Path) -> Path:
        path = pdf_path.expanduser()
        if not path.exists():
            raise InputError(f"PDF file does not exist: {path}")
        if not path.is_file():
            raise InputError(f"PDF path is not a regular file: {path}")
        if path.suffix.lower() != ".pdf":
            raise InputError(f"Expected a .pdf file: {path}")

        try:
            with path.open("rb") as file:
                header = file.read(PDF_HEADER_SCAN_BYTES)
        except OSError as error:
            raise PDFError(f"PDF file cannot be read: {path}") from error
        if b"%PDF-" not in header:
            raise PDFError(f"File content is not a valid PDF: {path}")
        return path

    @staticmethod
    def _open_reader(path: Path) -> PdfReader:
        try:
            reader = PdfReader(path, strict=False)
            if reader.is_encrypted:
                try:
                    decrypted = reader.decrypt("")
                except Exception as error:
                    raise PDFError(
                        "Encrypted PDF requires a password and cannot be read."
                    ) from error
                if not decrypted:
                    raise PDFError("Encrypted PDF requires a password and cannot be read.")
            if not reader.pages:
                raise EmptyPDFTextError("PDF contains no pages.")
            return reader
        except (PDFError, EmptyPDFTextError):
            raise
        except (PdfReadError, OSError, ValueError) as error:
            raise PDFError(f"PDF is corrupt, unsupported, or unreadable: {path}") from error

    @staticmethod
    def _page_has_images(page: object) -> bool:
        try:
            return bool(getattr(page, "images", []))
        except Exception:
            # If the image resources themselves are malformed, let normal PDF handling decide.
            return False

    @staticmethod
    def _meaningful_character_count(text: str) -> int:
        return sum(not character.isspace() for character in text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized_lines: list[str] = []
        for raw_line in text.replace("\x00", "").splitlines():
            line = re.sub(r"[\t\f\v ]+", " ", raw_line).strip()
            if line:
                normalized_lines.append(line)
        return "\n".join(normalized_lines)
