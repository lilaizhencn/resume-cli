"""Lazy local PaddleOCR adapter used only for scanned PDF pages."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from resume_cli.errors import OCRProcessingError, OCRUnavailableError

OCR_INSTALL_COMMAND = 'python -m pip install -e ".[ocr]"'
OCR_RENDER_DPI = 220
OCR_MIN_CONFIDENCE = 0.5


class OCREngine(Protocol):
    def recognize_page(self, pdf_path: Path, page_index: int) -> str: ...


class PaddleOCREngine:
    """Render one PDF page in memory and recognize Chinese/English text locally."""

    def __init__(self) -> None:
        self._pipeline: Any | None = None

    def recognize_page(self, pdf_path: Path, page_index: int) -> str:
        pipeline, pymupdf, numpy = self._load_runtime()
        try:
            with pymupdf.open(pdf_path) as document:
                page = document.load_page(page_index)
                scale = OCR_RENDER_DPI / 72
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
                image = numpy.frombuffer(pixmap.samples, dtype=numpy.uint8).reshape(
                    pixmap.height,
                    pixmap.width,
                    pixmap.n,
                )
                if pixmap.n > 3:
                    image = image[:, :, :3]

            results = pipeline.predict(image)
            return self._extract_text(results)
        except OCRUnavailableError:
            raise
        except Exception as error:
            raise OCRProcessingError(f"OCR failed on PDF page {page_index + 1}.") from error

    def _load_runtime(self) -> tuple[Any, Any, Any]:
        try:
            import numpy
            import pymupdf
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise OCRUnavailableError(
                "This PDF contains a scanned page, but OCR dependencies are not installed. "
                f"Install them with: {OCR_INSTALL_COMMAND}"
            ) from error

        if self._pipeline is None:
            try:
                self._pipeline = PaddleOCR(
                    lang="ch",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
            except Exception as error:
                raise OCRUnavailableError(
                    "PaddleOCR could not initialize its local inference runtime. "
                    f"Reinstall the OCR extra with: {OCR_INSTALL_COMMAND}"
                ) from error

        return self._pipeline, pymupdf, numpy

    @staticmethod
    def _extract_text(results: object) -> str:
        lines: list[str] = []
        for result in results or []:  # type: ignore[union-attr]
            payload = PaddleOCREngine._result_payload(result)
            texts = payload.get("rec_texts", [])
            scores = payload.get("rec_scores", [])
            for index, raw_text in enumerate(texts):
                text = str(raw_text).strip()
                score = float(scores[index]) if index < len(scores) else 1.0
                if text and score >= OCR_MIN_CONFIDENCE:
                    lines.append(text)
        return "\n".join(lines)

    @staticmethod
    def _result_payload(result: object) -> Mapping[str, Any]:
        candidate: object = result

        json_value = getattr(result, "json", None)
        if callable(json_value):
            candidate = json_value()
        elif json_value is not None:
            candidate = json_value

        if isinstance(candidate, Mapping):
            nested = candidate.get("res")
            if isinstance(nested, Mapping):
                return nested
            return candidate

        try:
            mapped = dict(candidate)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return {}
        nested = mapped.get("res")
        return nested if isinstance(nested, Mapping) else mapped
