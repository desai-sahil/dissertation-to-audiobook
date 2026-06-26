from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.cli import app
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Document, DocumentMeta
from thesis_audiobook.provenance import ProvenanceMap
from thesis_audiobook.stages import build_default_pipeline

runner = CliRunner()


def test_tiny_pipeline_renders_m4b_offline(tiny_ir_path: Path) -> None:
    """Full pipeline end to end on MockTts + MockMuxer: produces an M4B, no real calls."""
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    build_default_pipeline().run(Document(meta=DocumentMeta(title="x")), ctx)

    assert ctx.audio_outputs and ctx.audio_outputs[0].filename.endswith(".m4b")
    assert ctx.chapter_count >= 1
    assert ctx.provenance is not None and ctx.provenance.segments
    # The cost guard (autouse) would have raised had any real TTS/publish been reached.


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler pdftotext not installed")
def test_chapter6_sample_renders_m4b_via_cli(sample_pdf: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            str(sample_pdf),
            "--parser",
            "poppler",
            "--tts",
            "mock",
            "--out",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "no paid calls" in result.output

    m4bs = list(tmp_path.glob("*.m4b"))
    assert len(m4bs) == 1 and m4bs[0].stat().st_size > 0

    provs = list(tmp_path.glob("*.provenance.json"))
    assert len(provs) == 1
    prov = ProvenanceMap.model_validate_json(provs[0].read_text(encoding="utf-8"))
    assert prov.segments
    # The cache was populated, so a re-render would be served from disk.
    assert (tmp_path / "cache").exists()
