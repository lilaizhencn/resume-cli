from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from resume_cli.cli import app

runner = CliRunner()


def test_help_lists_required_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "parse" in result.stdout
    assert "extract" in result.stdout
    assert "score" in result.stdout
    assert "解析 PDF 简历" in result.stdout
    assert "Parse PDF resumes" in result.stdout


def test_command_help_is_bilingual() -> None:
    expected_text = {
        "parse": ("本地 PDF 简历路径", "Path to a local PDF resume"),
        "extract": ("提取并校验结构化简历", "Extract validated structured resume"),
        "score": ("评估简历与 JD", "Score resume-to-JD fit"),
    }

    for command, phrases in expected_text.items():
        result = runner.invoke(app, [command, "--help"])

        assert result.exit_code == 0
        assert all(phrase in result.stdout for phrase in phrases)


def test_mock_extract_outputs_valid_json_without_key(make_text_pdf, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pdf_path = make_text_pdf("Synthetic resume with Python and full-stack project experience")

    result = runner.invoke(app, ["extract", str(pdf_path), "--mock"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "李明"
    assert "Python" in payload["skills"]


def test_mock_score_outputs_and_saves_valid_json(make_text_pdf, tmp_path: Path) -> None:
    pdf_path = make_text_pdf("Synthetic resume with Python and full-stack project experience")
    jd_path = tmp_path / "jd.txt"
    jd_path.write_text("Python full-stack engineer; bachelor degree required", encoding="utf-8")
    output_path = tmp_path / "score.json"

    result = runner.invoke(
        app,
        [
            "score",
            str(pdf_path),
            "--jd",
            str(jd_path),
            "--mock",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["overall_score"] == 82
    assert json.loads(output_path.read_text(encoding="utf-8"))["overall_score"] == 82
    assert "Saved JSON" in result.stderr


def test_cli_errors_go_to_stderr(tmp_path: Path) -> None:
    result = runner.invoke(app, ["parse", str(tmp_path / "missing.pdf")])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "does not exist" in result.stderr
