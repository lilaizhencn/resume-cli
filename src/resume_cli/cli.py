"""Typer command-line interface."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, TypeVar

import typer

from resume_cli.ai import MockAIClient, OpenAIClient
from resume_cli.errors import ResumeCLIError
from resume_cli.output import model_to_pretty_json, write_output
from resume_cli.pdf_parser import PDFParser
from resume_cli.services import ResumeService

ResultT = TypeVar("ResultT")

app = typer.Typer(
    name="resume-cli",
    help=(
        "解析 PDF 简历、提取结构化信息并评估 JD 匹配度。 / "
        "Parse PDF resumes, extract structured information, and score JD fit."
    ),
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command("parse")
def parse_command(
    pdf_path: Annotated[
        Path,
        typer.Argument(help="本地 PDF 简历路径。 / Path to a local PDF resume."),
    ],
) -> None:
    """从 PDF 提取文本，必要时自动使用 OCR。 / Extract text, using OCR when needed."""

    _run(lambda: _parse(pdf_path))


@app.command("extract")
def extract_command(
    pdf_path: Annotated[
        Path,
        typer.Argument(help="本地 PDF 简历路径。 / Path to a local PDF resume."),
    ],
    mock: Annotated[
        bool,
        typer.Option(
            "--mock",
            help="使用确定性的离线 AI 输出。 / Use deterministic offline AI output.",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="将 JSON 保存到文件。 / Save JSON to a file."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="覆盖已存在的输出文件。 / Overwrite an existing output file.",
        ),
    ] = False,
) -> None:
    """提取并校验结构化简历 JSON。 / Extract validated structured resume JSON."""

    _run(lambda: _extract(pdf_path, mock=mock, output=output, force=force))


@app.command("score")
def score_command(
    pdf_path: Annotated[
        Path,
        typer.Argument(help="本地 PDF 简历路径。 / Path to a local PDF resume."),
    ],
    jd_path: Annotated[
        Path,
        typer.Option("--jd", help="UTF-8 JD 文本文件路径。 / Path to a UTF-8 JD text file."),
    ],
    mock: Annotated[
        bool,
        typer.Option(
            "--mock",
            help="使用确定性的离线 AI 输出。 / Use deterministic offline AI output.",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="将 JSON 保存到文件。 / Save JSON to a file."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="覆盖已存在的输出文件。 / Overwrite an existing output file.",
        ),
    ] = False,
) -> None:
    """评估简历与 JD 的匹配度。 / Score resume-to-JD fit as validated JSON."""

    _run(
        lambda: _score(
            pdf_path,
            jd_path=jd_path,
            mock=mock,
            output=output,
            force=force,
        )
    )


def _service(*, mock: bool | None = None) -> ResumeService:
    if mock is None:
        return ResumeService(PDFParser())
    factory = MockAIClient if mock else OpenAIClient.from_env
    return ResumeService(PDFParser(), factory)


def _parse(pdf_path: Path) -> None:
    typer.echo(_service().parse(pdf_path))


def _extract(pdf_path: Path, *, mock: bool, output: Path | None, force: bool) -> None:
    result = _service(mock=mock).extract(pdf_path)
    _emit_json(result_json=model_to_pretty_json(result), output=output, force=force)


def _score(
    pdf_path: Path,
    *,
    jd_path: Path,
    mock: bool,
    output: Path | None,
    force: bool,
) -> None:
    result = _service(mock=mock).score(pdf_path, jd_path)
    _emit_json(result_json=model_to_pretty_json(result), output=output, force=force)


def _emit_json(*, result_json: str, output: Path | None, force: bool) -> None:
    if output is not None:
        write_output(output, result_json, force=force)
        typer.echo(f"Saved JSON to {output.expanduser()}", err=True)
    typer.echo(result_json)


def _run(action: Callable[[], ResultT]) -> ResultT:
    try:
        return action()
    except ResumeCLIError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=error.exit_code) from error
    except Exception as error:
        typer.echo("Error: unexpected internal failure.", err=True)
        raise typer.Exit(code=1) from error
