from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.stages.narrate import NarrateStage
from thesis_audiobook.stages.vision_cartographer import VisionCartographerStage

_STRUCTURE = json.dumps(
    {
        "sections": [
            {"number": "I", "title": "INTRODUCTION", "start_page": 5, "kind": "body_chapter"}
        ]
    }
)


class _FakeVision:
    def __init__(self) -> None:
        self.calls = 0

    def describe(
        self,
        prompt: str,
        images: Sequence[bytes],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.calls += 1
        return _STRUCTURE


class _FakeLlm:
    def complete(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> str:
        if "rose to 0.5 units" in prompt:
            return "the value rose to zero point five units"
        if "held steady" in prompt:
            return "the value held steady"
        return "ok"


def _doc() -> Document:
    return Document(
        meta=DocumentMeta(title="t"),
        blocks=[
            Block(id="h1", type=BlockType.heading, page=5, text="I. INTRODUCTION"),
            Block(id="b1", type=BlockType.paragraph, page=5, text="the value rose to 0.5 units"),
            Block(id="b2", type=BlockType.paragraph, page=6, text="the value held steady"),
        ],
    )


def _v2_ctx(tiny_ir_path: Path):
    ctx = build_mock_context(Config(engine="v2"), pdf_bytes=b"pdf", mock_ir=tiny_ir_path)
    ctx.page_images = [b"page5", b"page6"]
    return ctx


def test_v2_stages_narrate_read_blocks(tiny_ir_path: Path) -> None:
    ctx = _v2_ctx(tiny_ir_path)
    ctx.vision = _FakeVision()
    ctx.llm = _FakeLlm()
    doc = _doc()
    VisionCartographerStage().run(doc, ctx)
    NarrateStage().run(doc, ctx)

    assert ctx.vision_structure is not None and len(ctx.vision_structure.sections) == 1
    by_id = {b.id: b for b in doc.blocks}
    assert by_id["b1"].spoken == "the value rose to zero point five units" and by_id["b1"].keep
    assert by_id["b2"].spoken == "the value held steady"
    assert by_id["b1"].chapter == 1  # mapped into body chapter I
    assert ctx.narration is not None and ctx.narration.narrated == 2
    assert len(ctx.narration.pairs) == 2


def test_vision_cartographer_caches_the_structure(tiny_ir_path: Path) -> None:
    ctx = _v2_ctx(tiny_ir_path)
    fake = _FakeVision()
    ctx.vision = fake
    VisionCartographerStage().run(_doc(), ctx)
    VisionCartographerStage().run(_doc(), ctx)  # identical pdf -> cache hit
    assert fake.calls == 1  # vision called once, second run served from cache (no re-bill)


def test_v2_stages_are_noop_under_v1_engine(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(engine="v1"), pdf_bytes=b"pdf", mock_ir=tiny_ir_path)
    ctx.vision = _FakeVision()
    doc = _doc()
    VisionCartographerStage().run(doc, ctx)
    NarrateStage().run(doc, ctx)
    assert ctx.vision_structure is None and ctx.narration is None
    assert all(b.spoken is None for b in doc.blocks)  # untouched


def test_v2_offline_with_mocks_is_safe_noop(tiny_ir_path: Path) -> None:
    # MockVision -> empty structure -> every block routes to review, narrated 0, no billing/crash.
    ctx = build_mock_context(Config(engine="v2"), pdf_bytes=b"pdf", mock_ir=tiny_ir_path)
    doc = _doc()
    VisionCartographerStage().run(doc, ctx)
    NarrateStage().run(doc, ctx)
    assert ctx.narration is not None and ctx.narration.narrated == 0
    assert ctx.narration.reviewed == 3  # all 3 blocks unmapped -> review, not shipped
