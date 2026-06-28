from __future__ import annotations

from thesis_audiobook.ir import Block, BlockType
from thesis_audiobook.page_align import assign_pages_by_text


def _b(bid: str, text: str) -> Block:
    return Block(id=bid, type=BlockType.paragraph, text=text)


_PAGES = [
    "Cover page. Transducing thermodynamic state of water.",
    "Climate change has caused extreme weather and large water stress in agriculture today.",
    "The micro tensiometer translates the water energy state into an electronic signal here.",
]


def test_assigns_pages_by_matching_block_text() -> None:
    blocks = [
        _b("p1", "Climate change has caused extreme weather and large water stress."),
        _b("p2", "The micro tensiometer translates the water energy state into a signal."),
    ]
    n = assign_pages_by_text(blocks, _PAGES)
    assert n == 2
    assert blocks[0].page == 2 and blocks[1].page == 3  # 1-indexed physical pages


def test_matches_globally_and_skips_unmatched() -> None:
    # global matching: a block is placed on its page even when an earlier block matched a later page
    # (Marker emits figures/captions out of physical order); an unmatched block is left as None.
    blocks = [
        _b("p3", "The micro tensiometer translates the water energy state into a signal."),  # p3
        _b("nope", "Entirely unrelated text that appears on no page at all whatsoever here."),
        _b("p2", "Climate change has caused extreme weather and large water stress."),  # p2
    ]
    assign_pages_by_text(blocks, _PAGES)
    assert blocks[0].page == 3
    assert blocks[1].page is None  # unmatched -> None (escalation skips it, never mis-locates)
    assert blocks[2].page == 2  # found on its real page even though it came after a page-3 block


def test_does_not_overwrite_an_existing_page() -> None:
    block = _b("p", "Climate change has caused extreme weather and large water stress.")
    block.page = 99  # already set (e.g. from a Marker anchor)
    assign_pages_by_text([block], _PAGES)
    assert block.page == 99


def test_too_short_signature_is_not_matched() -> None:
    blocks = [_b("h", "Intro")]  # below the minimum signature length -> ambiguous, skipped
    assert assign_pages_by_text(blocks, _PAGES) == 0
    assert blocks[0].page is None
