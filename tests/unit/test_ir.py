from __future__ import annotations

from pathlib import Path

from thesis_audiobook.ir import BlockType, Document


def test_tiny_ir_validates(tiny_ir_path: Path) -> None:
    doc = Document.model_validate_json(tiny_ir_path.read_text(encoding="utf-8"))
    assert doc.meta.title == "A Tiny Synthetic Thesis"
    assert len(doc.blocks) == 11
    assert doc.blocks[0].type is BlockType.frontmatter
    assert "fig1" in doc.figures


def test_ir_round_trips(tiny_ir_path: Path) -> None:
    doc = Document.model_validate_json(tiny_ir_path.read_text(encoding="utf-8"))
    assert Document.model_validate(doc.model_dump()) == doc
