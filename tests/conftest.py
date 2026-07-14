from __future__ import annotations

import base64
import io
from collections.abc import Callable
from pathlib import Path

import pytest
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


@pytest.fixture
def make_text_pdf(tmp_path: Path) -> Callable[[str, str], Path]:
    def _make(text: str, filename: str = "resume.pdf") -> Path:
        path = tmp_path / filename
        pdf = canvas.Canvas(str(path))
        if text:
            for line_number, line in enumerate(text.splitlines()):
                pdf.drawString(72, 760 - line_number * 18, line)
        pdf.showPage()
        pdf.save()
        return path

    return _make


@pytest.fixture
def make_image_pdf(tmp_path: Path) -> Callable[[], Path]:
    def _make() -> Path:
        # Synthetic one-pixel image; its content is irrelevant because OCR is faked.
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        path = tmp_path / "scanned.pdf"
        pdf = canvas.Canvas(str(path))
        pdf.drawImage(ImageReader(io.BytesIO(png)), 72, 600, width=200, height=100)
        pdf.showPage()
        pdf.save()
        return path

    return _make
