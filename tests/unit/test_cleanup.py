from __future__ import annotations

import pytest

from thesis_audiobook.cleanup import (
    classify_block,
    dehyphenate,
    ends_hyphenated,
    is_title_spillover,
    looks_like_page_number,
    normalize_ligatures,
    rejoin_split_tokens,
)
from thesis_audiobook.ir import BlockType


def test_dehyphenate_rejoins_line_break_words() -> None:
    assert dehyphenate("photosyn-\nthesis is key") == "photosynthesis is key"


def test_dehyphenate_flattens_line_breaks() -> None:
    assert dehyphenate("line one\nline two") == "line one line two"


def test_dehyphenate_rejoins_endash_compound_across_wrap() -> None:
    assert dehyphenate("the PYR–\nPP2C core") == "the PYR–PP2C core"


def test_normalize_ligatures() -> None:
    assert normalize_ligatures("eﬃcient ﬂow") == "efficient flow"


@pytest.mark.parametrize(
    "raw,joined",
    [
        ("g s", "gs"),
        ("g s /goxz", "gs /goxz"),
        ("H2 O2", "H2O2"),
        ("V PD", "VPD"),
        ("hosted by OZX", "hosted by OXZ"),  # transposition of the author's own "OXZ"
        ("OZXylem", "OZXylem"),  # word-bounded: not touched mid-word
    ],
)
def test_rejoin_split_tokens(raw: str, joined: str) -> None:
    assert rejoin_split_tokens(raw) == joined


@pytest.mark.parametrize("text", ["1", "17", "  3  "])
def test_looks_like_page_number(text: str) -> None:
    assert looks_like_page_number(text)


def test_not_page_number() -> None:
    assert not looks_like_page_number("Chapter 6")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("[12] Smith et al. Title.", BlockType.reference_list),
        ("- [3] Smith et al. Title. Journal, 2019.", BlockType.reference_list),  # markdown bullet
        ("CHAPTER 6", BlockType.heading),
        ("6.2 Results", BlockType.heading),
        ("Figure 1.1: Gradients in water potential.", BlockType.figure_caption),
        ("Table 4.1: Measured conductances.", BlockType.figure_caption),
        ("Figure A.7: Normalized difference in molar volume.", BlockType.figure_caption),
        # a body sentence opening with a figure reference (no colon) is NOT a caption
        ("Figure 2.1(c-j) present sketches of the pore states.", BlockType.paragraph),
        ("As shown in Figure 1.1, the gradient steepens.", BlockType.paragraph),
        ("A normal paragraph of prose.", BlockType.paragraph),
    ],
)
def test_classify_block(text: str, expected: BlockType) -> None:
    assert classify_block(text) is expected


def test_is_title_spillover() -> None:
    assert is_title_spillover("and A–gs modeling")
    assert not is_title_spillover("At present, the model resolves signaling.")


def test_ends_hyphenated() -> None:
    assert ends_hyphenated("catabolism via en-")
    assert not ends_hyphenated("a complete sentence.")
