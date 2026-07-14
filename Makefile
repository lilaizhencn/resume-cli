.PHONY: install install-ocr install-dev lint test help

install:
	python -m pip install -e .

install-ocr:
	python -m pip install -e '.[ocr]'

install-dev:
	python -m pip install -e '.[dev]'

lint:
	python -m ruff check .
	python -m ruff format --check .

test:
	python -m pytest

help:
	resume-cli --help
