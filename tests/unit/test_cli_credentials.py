from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from thesis_audiobook.cli import app

runner = CliRunner()


def test_real_llm_without_key_fails_cleanly(
    sample_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # --llm anthropic (turns on the curator) without a key must give a clear message,
    # not a raw SDK traceback, and exit before any network call.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(
        app,
        [
            "run",
            str(sample_pdf),
            "--parser",
            "poppler",
            "--llm",
            "anthropic",
            "--tts",
            "mock",
            "--out",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "c"),
        ],
    )
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY" in result.output


def test_real_tts_without_key_fails_cleanly(
    sample_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVEN_LABS_API_KEY", raising=False)
    result = runner.invoke(
        app,
        [
            "run",
            str(sample_pdf),
            "--parser",
            "poppler",
            "--tts",
            "elevenlabs",
            "--voice",
            "v123",
            "--out",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "c"),
        ],
    )
    assert result.exit_code == 2
    assert "ELEVENLABS_API_KEY" in result.output
