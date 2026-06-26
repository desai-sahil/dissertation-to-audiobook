from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from thesis_audiobook.cli import app

runner = CliRunner()

_needs_poppler = pytest.mark.skipif(
    shutil.which("pdftotext") is None, reason="poppler pdftotext not installed"
)


@_needs_poppler
def test_dry_run_estimates_cost_with_zero_external_calls(sample_pdf: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            str(sample_pdf),
            "--dry-run",
            "--parser",
            "poppler",
            "--out",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "no external calls" in result.output
    assert "estimated USD" in result.output
    assert "chunk plan" in result.output
    # Cost-estimate only: no audio rendered, and nothing reached the cache.
    assert not list(tmp_path.glob("*.m4b"))
    assert not (tmp_path / "cache").exists()
