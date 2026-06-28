from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from thesis_audiobook.cli import app

runner = CliRunner()


def test_run_v2_offline_smoke(tmp_path: Path) -> None:
    """`run-v2 --llm mock` is a free offline no-op: it ingests, runs the v2 stages on mocks
    (empty structure -> nothing narrated), and still writes the script + pairs sidecar. Proves the
    wiring end to end without billing."""
    md = tmp_path / "thesis.md"
    md.write_text("# A Tiny Thesis\n\nThis is one paragraph of body text.\n", encoding="utf-8")
    pdf = tmp_path / "thesis.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")  # not rendered under --llm mock

    result = runner.invoke(
        app,
        [
            "run-v2",
            str(pdf),
            "--markdown",
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
    assert "v2 engine" in result.output
    outs = list((tmp_path / "out").glob("*.v2-pairs.json"))
    assert outs, "pairs sidecar was written"
    assert list((tmp_path / "out").glob("*.script.md")), "script was written"
