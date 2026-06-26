from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, committee_profile, general_profile
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta, Handling
from thesis_audiobook.stages.select import SelectStage


def _doc() -> Document:
    types = [
        BlockType.paragraph,
        BlockType.heading,
        BlockType.frontmatter,
        BlockType.reference_list,
        BlockType.table,
        BlockType.equation_display,
        BlockType.figure_caption,
        BlockType.backmatter,
        BlockType.footnote,
        BlockType.code,
    ]
    blocks = [Block(id=str(t.value), type=t, text="x") for t in types]
    return Document(meta=DocumentMeta(title="t"), blocks=blocks)


def _selected(profile_name: str, tiny_ir_path: Path) -> dict[str, Block]:
    profile = committee_profile() if profile_name == "committee" else general_profile()
    ctx = build_mock_context(Config(profile=profile), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    doc = SelectStage().run(_doc(), ctx)
    return {block.id: block for block in doc.blocks}


def test_paragraph_and_heading_are_spoken(tiny_ir_path: Path) -> None:
    blocks = _selected("committee", tiny_ir_path)
    for key in ("paragraph", "heading"):
        assert blocks[key].keep is True
        assert blocks[key].handling is Handling.speak


def test_frontmatter_and_refs_skipped(tiny_ir_path: Path) -> None:
    blocks = _selected("committee", tiny_ir_path)
    for key in ("frontmatter", "reference_list", "figure_caption", "footnote", "code"):
        assert blocks[key].keep is False
        assert blocks[key].handling is Handling.skip


def test_table_handling_differs_by_profile(tiny_ir_path: Path) -> None:
    assert _selected("committee", tiny_ir_path)["table"].handling is Handling.summarize
    assert _selected("general", tiny_ir_path)["table"].handling is Handling.skip


def test_equation_handling_differs_by_profile(tiny_ir_path: Path) -> None:
    assert _selected("committee", tiny_ir_path)["equation_display"].handling is Handling.gloss
    assert _selected("general", tiny_ir_path)["equation_display"].handling is Handling.announce


def test_backmatter_skipped_without_appendices(tiny_ir_path: Path) -> None:
    assert _selected("committee", tiny_ir_path)["backmatter"].keep is False
