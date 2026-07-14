"""Application errors translated to stable CLI exit codes."""


class ResumeCLIError(Exception):
    """Base class for expected, user-facing errors."""

    exit_code = 1


class InputError(ResumeCLIError):
    """Invalid input path or content."""

    exit_code = 2


class PDFError(ResumeCLIError):
    """PDF validation or parsing failed."""

    exit_code = 3


class EmptyPDFTextError(PDFError):
    """No useful text could be extracted from a PDF."""


class OCRUnavailableError(PDFError):
    """A scanned page needs OCR but the optional runtime is unavailable."""

    exit_code = 4


class OCRProcessingError(PDFError):
    """OCR was available but failed to process a page."""

    exit_code = 4


class OCREmptyResultError(OCRProcessingError):
    """OCR completed but found no usable text on a scanned page."""


class ConfigurationError(ResumeCLIError):
    """Required environment configuration is missing or invalid."""

    exit_code = 5


class AIServiceError(ResumeCLIError):
    """The configured AI provider request failed."""

    exit_code = 6


class AIResponseError(ResumeCLIError):
    """The AI provider returned an unusable response."""

    exit_code = 7


class OutputError(ResumeCLIError):
    """A requested output artifact could not be written."""

    exit_code = 8
