from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, Profile, committee_profile, general_profile
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta, Handling
from thesis_audiobook.lexicon import DEFAULT_LEXICON
from thesis_audiobook.stages.figures import FiguresStage, clean_caption


def test_clean_caption() -> None:
    out = clean_caption("Fig. 1. (A) gs over time. (B) CO2 response.", DEFAULT_LEXICON)
    assert out == "Figure one. Panel A stomatal conductance over time. Panel B C O two response."


def _ctx(profile: Profile, tiny_ir_path: Path) -> Context:
    return build_mock_context(Config(profile=profile), pdf_bytes=b"x", mock_ir=tiny_ir_path)


def _table_doc() -> Document:
    block = Block(id="t1", type=BlockType.table, text="WT 0.3 | mutant 0.1", keep=True)
    return Document(meta=DocumentMeta(title="t"), blocks=[block])


def test_committee_summarizes_table_via_llm(tiny_ir_path: Path) -> None:
    doc = FiguresStage().run(_table_doc(), _ctx(committee_profile(), tiny_ir_path))
    block = doc.blocks[0]
    assert block.handling is Handling.summarize
    assert block.spoken is not None
    assert block.spoken.startswith("Table one.")
    assert "mock gloss" in block.spoken


def test_general_skips_table_with_note(tiny_ir_path: Path) -> None:
    doc = FiguresStage().run(_table_doc(), _ctx(general_profile(), tiny_ir_path))
    block = doc.blocks[0]
    assert block.handling is Handling.skip
    assert block.spoken == "Table one is omitted from the audio."
