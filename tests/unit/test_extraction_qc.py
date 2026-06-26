from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from thesis_audiobook.cli import app
from thesis_audiobook.extraction_qc import build_qc_prompt, parse_qc, render_qc_md

runner = CliRunner()

_REPORT_JSON = (
    '{"summary":"Mostly clean; a few equation issues.",'
    '"issues":[{"kind":"broken_equation","severity":"high","location":"Section 2.3, '
    '\\"$$ ... $$\\"","detail":"display equation truncated","suggestion":"re-extract p.21"},'
    '{"kind":"ocr_garble","severity":"low","location":"Ch4","detail":"stray chars",'
    '"suggestion":"minor"}]}'
)


def test_build_qc_prompt_includes_markdown_and_shape() -> None:
    prompt = build_qc_prompt("# Intro\n\nSome body.")
    assert "Some body." in prompt and "EXTRACTION DEFECTS" in prompt and '"issues"' in prompt


def test_parse_qc_valid_fenced_and_garbage() -> None:
    report = parse_qc(f"```json\n{_REPORT_JSON}\n```")
    assert len(report.issues) == 2
    assert report.issues[0].kind == "broken_equation"
    # A non-JSON response (offline mock) degrades to an empty report, not a crash.
    assert parse_qc("a mock gloss for input abcd").is_empty()


def test_render_qc_md_sorts_by_severity_and_handles_empty() -> None:
    assert "No extraction issues" in render_qc_md(parse_qc("not json"))
    md = render_qc_md(parse_qc(_REPORT_JSON))
    assert "## Summary" in md and "broken_equation" in md
    # high-severity row precedes the low-severity one
    assert md.index("broken_equation") < md.index("ocr_garble")


def test_check_extraction_cli_offline_is_noop(tmp_path: Path) -> None:
    md = tmp_path / "thesis.md"
    md.write_text("# Intro\n\nClean text.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "check-extraction",
            str(md),
            "--llm",
            "mock",
            "--out",
            str(tmp_path / "out"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "issues   : 0" in result.output
    assert (tmp_path / "out" / "thesis.extraction-qc.md").exists()


def test_check_extraction_missing_file_errors(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check-extraction", str(tmp_path / "nope.md"), "--llm", "mock"])
    assert result.exit_code == 2
