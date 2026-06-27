from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.stages.structurer import StructurerStage
from thesis_audiobook.structurer import (
    apply_structure,
    build_outline,
    parse_structure_plan,
)

_PLAN = (
    '{"labels":[{"id":"m1","kind":"prose"},{"id":"m2","kind":"code"},'
    '{"id":"m3","kind":"reference"},{"id":"m4","kind":"boguskind"}]}'
)


class _FakeLlm:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return self.response


def _blocks() -> list[Block]:
    return [
        Block(id="m1", type=BlockType.paragraph, text="A normal sentence of prose."),
        Block(id="m2", type=BlockType.paragraph, text="i m p o rt p a n d a s a s pd"),
        Block(id="m3", type=BlockType.paragraph, text="Smith, J. A title. Journal, 2019."),
        Block(id="m4", type=BlockType.paragraph, text="Another paragraph."),
    ]


def test_outline_lists_every_block_with_id_and_type() -> None:
    outline = build_outline(_blocks())
    assert "m2 | paragraph | i m p o rt" in outline
    assert outline.count("\n") == 3  # one line per block


def test_parse_handles_garbage() -> None:
    assert parse_structure_plan("not json").is_empty()
    assert len(parse_structure_plan(f"```json\n{_PLAN}\n```").labels) == 4


def test_apply_sets_types_logs_changes_and_ignores_unknowns() -> None:
    blocks = _blocks()
    changes = apply_structure(blocks, parse_structure_plan(_PLAN))
    kinds = {b.id: b.type for b in blocks}
    assert kinds["m1"] is BlockType.paragraph  # unchanged (already prose)
    assert kinds["m2"] is BlockType.code  # spaced-out code reclassified
    assert kinds["m3"] is BlockType.reference_list
    assert kinds["m4"] is BlockType.paragraph  # unknown kind ignored, left as-is
    # the change log records only the two real reclassifications, with provenance
    assert {c.id for c in changes} == {"m2", "m3"}
    m2 = next(c for c in changes if c.id == "m2")
    assert m2.from_type == "paragraph" and m2.to_type == "code"


def test_stage_mock_is_noop(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    doc = Document(meta=DocumentMeta(title="t"), blocks=_blocks())
    StructurerStage().run(doc, ctx)
    assert all(b.type is BlockType.paragraph for b in doc.blocks)  # mock -> empty -> no change
    assert ctx.reclassifications == []


def test_stage_applies_and_caches(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_PLAN)
    ctx.llm = fake
    doc = Document(meta=DocumentMeta(title="t"), blocks=_blocks())
    StructurerStage().run(doc, ctx)
    assert next(b for b in doc.blocks if b.id == "m2").type is BlockType.code
    assert len(ctx.reclassifications) == 2
    assert any("reclassified" in w.reason for w in ctx.warnings.items)
    StructurerStage().run(Document(meta=DocumentMeta(title="t"), blocks=_blocks()), ctx)
    assert fake.calls == 1  # same blocks -> cached, no second call


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(structurer=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_PLAN)
    ctx.llm = fake
    doc = Document(meta=DocumentMeta(title="t"), blocks=_blocks())
    StructurerStage().run(doc, ctx)
    assert fake.calls == 0 and all(b.type is BlockType.paragraph for b in doc.blocks)
