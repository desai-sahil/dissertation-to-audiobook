from __future__ import annotations

from pathlib import Path

from thesis_audiobook.adapters.poppler_parser import parse_document
from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Document
from thesis_audiobook.stages.build_ir import BuildIrStage


def _sample_ir(cassette_dir: Path, tiny_ir_path: Path) -> Document:
    """Parse the recorded sample text and run build_ir, offline (no poppler needed)."""
    text = (cassette_dir / "chapter6.pdftotext.txt").read_text(encoding="utf-8")
    doc = parse_document(text)
    ctx = build_mock_context(Config(), pdf_bytes=b"", mock_ir=tiny_ir_path, log_enabled=False)
    return BuildIrStage().run(doc, ctx)


def test_sample_ir_matches_golden(cassette_dir: Path, golden_dir: Path, tiny_ir_path: Path) -> None:
    produced = _sample_ir(cassette_dir, tiny_ir_path)
    golden = Document.model_validate_json(
        (golden_dir / "chapter6.ir.json").read_text(encoding="utf-8")
    )
    assert produced.model_dump() == golden.model_dump()
