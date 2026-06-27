from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, Profile, committee_profile, general_profile
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta, Handling
from thesis_audiobook.stages.math import MathStage, equation_number


def _ctx(profile: Profile, tiny_ir_path: Path) -> Context:
    return build_mock_context(Config(profile=profile), pdf_bytes=b"x", mock_ir=tiny_ir_path)


def _doc(latex: str) -> Document:
    block = Block(id="eq", type=BlockType.equation_display, text=latex, latex=latex, keep=True)
    return Document(meta=DocumentMeta(title="t"), blocks=[block])


def test_equation_number_extraction() -> None:
    assert equation_number(r"\psi = \frac{RT}{v} \ln(x) \tag{2.4}") == "2.4"
    assert equation_number(r"P = p_{sat} + RT \tag{ (2.13) }") == "2.13"  # tag may wrap parens
    assert equation_number(r"= \mu_o(T) + v(P - p) (2.9)") == "2.9"  # trailing bare number
    assert equation_number(r"\mu^{liq}(P,T) = \mu^{vap}(p,T)") is None  # unnumbered step


def test_numbered_equation_announced_by_real_number(tiny_ir_path: Path) -> None:
    # The thesis's own number is spoken (matching the prose's "in Equation 2.4"), not an ordinal.
    doc = MathStage().run(
        _doc(r"\psi = RT \ln(x) \tag{2.4}"), _ctx(committee_profile(), tiny_ir_path)
    )
    block = doc.blocks[0]
    assert block.handling is Handling.announce
    assert block.spoken == "Equation two point four."


def test_unnumbered_equation_is_dropped(tiny_ir_path: Path) -> None:
    # No tag/number to announce and the formula is not read aloud, so it leaves the audio.
    doc = MathStage().run(_doc(r"\mu^{liq} = \mu^{vap}"), _ctx(general_profile(), tiny_ir_path))
    block = doc.blocks[0]
    assert block.spoken is None and block.keep is False and block.handling is Handling.skip


def test_no_llm_call_on_either_profile(tiny_ir_path: Path) -> None:
    # The math stage never calls the LLM now; the autouse cost guard would fail a real call.
    for profile in (committee_profile(), general_profile()):
        doc = MathStage().run(_doc(r"x = y \tag{1.1}"), _ctx(profile, tiny_ir_path))
        assert doc.blocks[0].spoken == "Equation one point one."


def test_full_tier_is_not_implemented(tiny_ir_path: Path) -> None:
    ctx = _ctx(Profile(name="full-test", equation_tier="full"), tiny_ir_path)
    with pytest.raises(NotImplementedError):
        MathStage().run(_doc(r"x = y \tag{1.1}"), ctx)
