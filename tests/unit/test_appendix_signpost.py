from __future__ import annotations

from thesis_audiobook.appendix_signpost import APPENDIX_SIGNPOST, apply_signposts
from thesis_audiobook.ir import Block, BlockType, Handling


def _b(bid: str, text: str, chapter: int | None, *, keep: bool = True) -> Block:
    return Block(
        id=bid,
        type=BlockType.paragraph,
        text=text,
        chapter=chapter,
        keep=keep,
        handling=Handling.speak,
    )


def test_signpost_added_once_per_chapter_on_first_reference() -> None:
    blocks = [
        _b("b1", "Intro with no reference.", 1),
        _b("b2", "As shown in Appendix C, the method works.", 1),  # first ref in ch1
        _b("b3", "Again see Appendix C for more.", 1),  # second ref: no signpost
        _b("b4", "Chapter two body, see Appendix D.", 2),  # first ref in ch2
    ]
    count = apply_signposts(blocks, include_appendices=False)
    assert count == 2
    assert blocks[0].spoken is None  # no reference
    assert blocks[1].spoken is not None and APPENDIX_SIGNPOST in blocks[1].spoken
    assert blocks[1].spoken.startswith("As shown in Appendix C")  # original text preserved verbatim
    assert blocks[2].spoken is None  # "point and move on" - no second signpost in ch1
    assert blocks[3].spoken is not None and APPENDIX_SIGNPOST in blocks[3].spoken


def test_signpost_matches_plural_appendices() -> None:
    blocks = [_b("b1", "See Appendices A and B for the derivations.", 1)]
    assert apply_signposts(blocks, include_appendices=False) == 1
    assert blocks[0].spoken is not None and APPENDIX_SIGNPOST in blocks[0].spoken


def test_signpost_noop_when_appendices_included() -> None:
    blocks = [_b("b1", "See Appendix C.", 1)]
    assert apply_signposts(blocks, include_appendices=True) == 0
    assert blocks[0].spoken is None


def test_signpost_ignores_plain_word_and_skipped_blocks() -> None:
    blocks = [
        _b("b1", "We added an appendix to the report.", 1),  # lowercase, generic: no match
        _b("b2", "See Appendix A.", 2, keep=False),  # skipped block: ignored
        _b("b3", "Front matter, see Appendix A.", None),  # no chapter: ignored
    ]
    assert apply_signposts(blocks, include_appendices=False) == 0
    assert all(b.spoken is None for b in blocks)
