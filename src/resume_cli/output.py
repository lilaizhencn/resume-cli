"""Terminal-safe JSON serialization and optional file output."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from resume_cli.errors import OutputError


def model_to_pretty_json(model: BaseModel) -> str:
    return model.model_dump_json(indent=2)


def write_output(path: Path, content: str, *, force: bool) -> None:
    output_path = path.expanduser()
    if not output_path.parent.exists():
        raise OutputError(f"Output directory does not exist: {output_path.parent}")
    if output_path.exists() and output_path.is_dir():
        raise OutputError(f"Output path is a directory: {output_path}")
    if output_path.exists() and not force:
        raise OutputError(
            f"Output file already exists: {output_path}. Pass --force to overwrite it."
        )

    try:
        output_path.write_text(content + "\n", encoding="utf-8")
    except OSError as error:
        raise OutputError(f"Could not write output file: {output_path}") from error
