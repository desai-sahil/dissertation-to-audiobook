from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, Profile, committee_profile, general_profile
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta, Handling
from thesis_audiobook.stages.math import MathStage, gloss_prompt


def _ctx(profile: Profile, tiny_ir_path: Path) -> Context:
    return build_mock_context(Config(profile=profile), pdf_bytes=b"x", mock_ir=tiny_ir_path)


def _equation_doc() -> Document:
    block = Block(
        id="eq", type=BlockType.equation_display, text="g_s = f(x)", latex="g_s = f(x)", keep=True
    )
    return Document(meta=DocumentMeta(title="t"), blocks=[block])


def test_gloss_prompt_includes_latex() -> None:
    assert "g_s = f(x)" in gloss_prompt("g_s = f(x)")


def test_committee_glosses_via_llm(tiny_ir_path: Path) -> None:
    doc = MathStage().run(_equation_doc(), _ctx(committee_profile(), tiny_ir_path))
    block = doc.blocks[0]
    assert block.handling is Handling.gloss
    assert block.spoken is not None
    assert block.spoken.startswith("Equation one.")
    assert "mock gloss" in block.spoken  # populated from MockLlm


def test_general_announces_without_llm(tiny_ir_path: Path) -> None:
    doc = MathStage().run(_equation_doc(), _ctx(general_profile(), tiny_ir_path))
    block = doc.blocks[0]
    assert block.handling is Handling.announce
    assert block.spoken == "Equation one is shown in the text here."


def test_full_tier_is_not_implemented(tiny_ir_path: Path) -> None:
    ctx = _ctx(Profile(name="full-test", equation_tier="full"), tiny_ir_path)
    with pytest.raises(NotImplementedError):
        MathStage().run(_equation_doc(), ctx)
