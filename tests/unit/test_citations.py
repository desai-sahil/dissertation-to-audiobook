from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta, Handling
from thesis_audiobook.stages.citations import CitationsStage


class _FakeLlm:
    """Returns a fixed genericization map for the genericize prompt; counts calls."""

    def __init__(self, mapping_json: str) -> None:
        self.mapping_json = mapping_json
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return self.mapping_json


def _doc(*texts: str) -> Document:
    blocks = [
        Block(id=f"b{i}", type=BlockType.paragraph, text=t, keep=True, handling=Handling.speak)
        for i, t in enumerate(texts)
    ]
    return Document(meta=DocumentMeta(title="t"), blocks=blocks)


def test_strips_markers_offline(tiny_ir_path: Path) -> None:
    # offline (mock LLM) -> no genericizing, but markers are still stripped deterministically
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    doc = _doc("the response (Geiger et al., 2009) was rapid.41 and shown in [12]")
    CitationsStage().run(doc, ctx)
    assert doc.blocks[0].spoken == "the response was rapid. and shown in"


def test_genericizes_narrative_mentions_with_llm(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ctx.llm = _FakeLlm('{"Chalmer et al.": "researchers"}')
    doc = _doc("Chalmer et al. note that water deficit helps.18")
    CitationsStage().run(doc, ctx)
    assert doc.blocks[0].spoken == "researchers note that water deficit helps."


def test_genericize_is_cached(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm('{"Chalmer et al.": "researchers"}')
    ctx.llm = fake
    CitationsStage().run(_doc("Chalmer et al. note this"), ctx)
    CitationsStage().run(_doc("Chalmer et al. note this"), ctx)  # same mentions -> cache hit
    assert fake.calls == 1


def test_no_llm_call_when_no_narrative_mentions(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm("{}")
    ctx.llm = fake
    doc = _doc("a plain sentence with a bracket [12] only")
    CitationsStage().run(doc, ctx)
    assert fake.calls == 0  # nothing narrative -> no model call
    assert doc.blocks[0].spoken == "a plain sentence with a bracket only"


def test_curate_disabled_skips_llm_but_still_strips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(curate=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm('{"Chalmer et al.": "researchers"}')
    ctx.llm = fake
    doc = _doc("Chalmer et al. note that.18")
    CitationsStage().run(doc, ctx)
    assert fake.calls == 0
    assert doc.blocks[0].spoken == "Chalmer and others note that."  # degrades, not genericized
