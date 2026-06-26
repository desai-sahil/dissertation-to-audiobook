from __future__ import annotations

from pathlib import Path

from thesis_audiobook.ir import BlockType
from thesis_audiobook.markdown_ir import markdown_to_document


def test_markdown_to_document(cassette_dir: Path) -> None:
    markdown = (cassette_dir / "marker_sample.md").read_text(encoding="utf-8")
    doc = markdown_to_document(markdown, title="Sample")
    types = [block.type for block in doc.blocks]

    assert doc.meta.title == "Sample"
    assert BlockType.heading in types
    assert BlockType.paragraph in types
    assert BlockType.figure_caption in types
    assert BlockType.table in types

    sections = {block.section for block in doc.blocks if block.section}
    assert {"6.1", "6.2"} <= sections

    captions = [b.text for b in doc.blocks if b.type is BlockType.figure_caption]
    assert captions == ["Figure 1. Gas exchange over time."]
