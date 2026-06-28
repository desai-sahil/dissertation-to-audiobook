from __future__ import annotations

from thesis_audiobook.engine import (
    EngineOutcome,
    map_structure_to_blocks,
    narrate_document,
    review_gate,
)
from thesis_audiobook.ir import Block, BlockType
from thesis_audiobook.vision_structure import VisionSection, VisionStructureMap


def _block(bid: str, text: str, btype: BlockType = BlockType.paragraph) -> Block:
    return Block(id=bid, type=btype, text=text)


# The structure is anchored to the IR's headings by their printed text, NOT by page (vision's page
# estimates drift). Section start_page is irrelevant to the mapping and intentionally omitted.
_MAP = VisionStructureMap(
    sections=[
        VisionSection(number="", title="Abstract", kind="abstract"),
        VisionSection(number="I", title="INTRODUCTION", kind="body_chapter"),
        VisionSection(number="II", title="BACKGROUND", kind="body_chapter"),
        VisionSection(number="VII", title="REFERENCES", kind="references"),
    ]
)


def _doc_blocks() -> list[Block]:
    return [
        _block("title", "Title page material"),  # before any matched heading -> review
        _block("h_abs", "Abstract", BlockType.heading),  # matches abstract -> read
        _block("abs", "Abstract reports 0.5 units"),  # narrate
        _block("h1", "I. INTRODUCTION", BlockType.heading),  # matches chapter I
        _block("p1", "increased by 0.5 units"),  # narrate (ok)
        _block("sub", "I.A. Sub-section heading", BlockType.heading),  # no match -> inherits chap I
        _block("h2", "II. BACKGROUND", BlockType.heading),  # matches chapter II
        _block("p2", "decreased by 0.9"),  # narrate (fails -> held)
        _block("h_ref", "VII. REFERENCES", BlockType.heading),  # matches references -> skip
        _block("ref", "[1] Smith et al."),  # under references -> skip
    ]


def _fake_generate(prompt: str) -> str:
    if "Abstract reports 0.5 units" in prompt:
        return "Abstract reports zero point five units"
    if "increased by 0.5 units" in prompt:
        return "increased by zero point five units"
    if "decreased by 0.9" in prompt:
        return "decreased by zero point one"  # 0.9 -> 0.1: value changed
    return "ok"


def test_map_anchors_sections_to_headings() -> None:
    a = map_structure_to_blocks(_doc_blocks(), _MAP)
    assert a["title"].decision == "review" and a["title"].kind == "unmapped"
    assert (
        a["h_abs"].decision == "read"
        and a["h_abs"].kind == "abstract"
        and a["h_abs"].chapter is None
    )
    assert a["abs"].decision == "read"
    assert a["h1"].decision == "read" and a["h1"].chapter == 1
    assert a["p1"].chapter == 1
    assert a["sub"].decision == "read" and a["sub"].chapter == 1  # subsection inherits chapter I
    assert a["h2"].chapter == 2
    assert a["p2"].chapter == 2
    assert a["h_ref"].decision == "skip" and a["h_ref"].kind == "references"
    assert a["ref"].decision == "skip"


def test_narrate_document_routes_each_block() -> None:
    blocks = _doc_blocks()
    by_id = {b.id: b for b in blocks}
    outcome = narrate_document(
        blocks, map_structure_to_blocks(blocks, _MAP), generate=_fake_generate
    )

    assert by_id["p1"].spoken == "increased by zero point five units" and by_id["p1"].keep
    assert by_id["abs"].spoken and by_id["abs"].keep
    assert by_id["h1"].keep and by_id["h1"].spoken is None and by_id["h1"].chapter == 1  # announced
    assert by_id["ref"].keep is False  # references -> skipped
    assert by_id["title"].keep is False  # pre-section -> review
    assert by_id["p2"].keep is False  # verifier-failed narration is held, not shipped

    assert outcome.narrated == 2 and outcome.held == 1
    assert outcome.skipped == 2 and outcome.reviewed == 1  # skipped: h_ref + ref; review: title
    assert len(outcome.pairs) == 3  # abs, p1, p2 attempted
    reasons = {f.block_id: f.reason for f in outcome.flagged}
    assert reasons == {"title": "review", "p2": "verifier"}


def test_match_is_by_title_not_number() -> None:
    # Gao-style: vision puts the number in its noisy `number` field ("1", "CHAPTER 3"), but the IR
    # heading text has none (Marker's "CHAPTER N" divider was stripped). Matching on the title
    # bridges this and Zhu's number-in-text headings; otherwise the chapters fall through to skip.
    smap = VisionStructureMap(
        sections=[
            VisionSection(number="1", title="Introduction", kind="body_chapter"),
            VisionSection(number="CHAPTER 3", title="Results and Discussion", kind="body_chapter"),
        ]
    )
    blocks = [
        _block("h1", "INTRODUCTION", BlockType.heading),
        _block("p1", "some prose"),
        _block("h2", "RESULTS AND DISCUSSION", BlockType.heading),
        _block("p2", "more prose"),
    ]
    a = map_structure_to_blocks(blocks, smap)
    assert a["h1"].decision == "read" and a["h1"].chapter == 1
    assert a["h2"].decision == "read" and a["h2"].chapter == 2
    assert a["p1"].chapter == 1 and a["p2"].chapter == 2


def test_announce_hook_handles_equations_tables_and_subsection_headings() -> None:
    from thesis_audiobook.equations import equation_announcement

    blocks = [
        _block("h1", "I. INTRODUCTION", BlockType.heading),  # chapter-start heading
        Block(id="eq", type=BlockType.equation_display, text="x", latex=r"x = y \tag{1.2}"),
        Block(id="eq0", type=BlockType.equation_display, text="z", latex=r"z = w"),  # unnumbered
        Block(id="tab", type=BlockType.table, text="| a | b |"),
        _block("sub", "I.A. Methods detail", BlockType.heading),  # subsection heading
    ]

    def announce(b: Block) -> str | None:
        if b.type is BlockType.equation_display:
            return equation_announcement(b.latex or b.text)
        if b.type is BlockType.table:
            return "A table is shown here."
        return None

    by = {b.id: b for b in blocks}
    outcome = narrate_document(
        blocks, map_structure_to_blocks(blocks, _MAP), generate=lambda _p: "x", announce=announce
    )
    assert by["eq"].spoken == "Equation one point two." and by["eq"].keep  # announced by number
    assert by["eq0"].keep is False  # unnumbered equation -> skipped
    assert by["tab"].spoken == "A table is shown here." and by["tab"].keep
    assert outcome.announced == 2  # eq + table (bypass the verifier)
    assert by["h1"].chapter == 1  # chapter-start heading keeps "Chapter N"
    assert by["sub"].chapter is None  # subsection heading -> no repeated "Chapter N"


def test_ordered_matching_avoids_duplicate_chapter_from_repeated_subsection_title() -> None:
    # Gao trap: a chapter's internal "Conclusion" subsection repeats a (noisy) vision section title.
    # Ordered one-to-one matching consumes each section once, so the repeat stays a subsection.
    smap = VisionStructureMap(
        sections=[
            VisionSection(number="1", title="Introduction", kind="body_chapter"),
            VisionSection(number="2", title="Methods", kind="body_chapter"),
        ]
    )
    blocks = [
        _block("h1", "INTRODUCTION", BlockType.heading),
        _block("c1", "Conclusion", BlockType.heading),  # subsection inside chapter 1
        _block("h2", "METHODS", BlockType.heading),
        _block("c2", "Conclusion", BlockType.heading),  # subsection inside chapter 2
    ]
    a = map_structure_to_blocks(blocks, smap)
    assert a["h1"].section_head and a["h1"].chapter == 1
    assert a["h2"].section_head and a["h2"].chapter == 2
    assert not a["c1"].section_head and not a["c2"].section_head  # subsections, not chapter starts


def test_parallel_narration_is_order_preserving_and_identical() -> None:
    # max_workers > 1 must produce byte-identical output to sequential (results applied in order).
    def gen(prompt: str) -> str:
        if "alpha 0.5" in prompt:
            return "alpha zero point five"
        if "beta 0.9" in prompt:
            return "beta zero point nine"
        return "ok"

    def build() -> list[Block]:
        return [
            _block("h", "I. INTRODUCTION", BlockType.heading),
            _block("p1", "alpha 0.5"),
            _block("p2", "beta 0.9"),
        ]

    seq, par = build(), build()
    o1 = narrate_document(seq, map_structure_to_blocks(seq, _MAP), generate=gen, max_workers=1)
    o2 = narrate_document(par, map_structure_to_blocks(par, _MAP), generate=gen, max_workers=8)
    assert [b.spoken for b in seq] == [b.spoken for b in par]
    assert [p.model_dump() for p in o1.pairs] == [p.model_dump() for p in o2.pairs]
    assert o1.narrated == o2.narrated == 2


def test_review_gate_flags_high_held_or_review_rate() -> None:
    assert review_gate(EngineOutcome(narrated=10, held=0, reviewed=1)) is None  # 1/11 = 9% <= 15%
    assert review_gate(EngineOutcome(narrated=0)) is not None  # nothing narrated
    flagged = review_gate(EngineOutcome(narrated=5, held=3, reviewed=2))  # 5/10 = 50% > 15%
    assert flagged is not None and "review" in flagged


def test_narration_is_bounded_per_block() -> None:
    # cost safety: a block that never verifies makes at most max_text_attempts calls, then stops.
    calls = {"n": 0}

    def always_bad(_prompt: str) -> str:
        calls["n"] += 1
        return "decreased by zero point one"  # never satisfies 0.9

    blocks = [
        _block("h", "I. INTRODUCTION", BlockType.heading),  # so the paragraph is in a read section
        _block("p", "decreased by 0.9"),
    ]
    narrate_document(
        blocks, map_structure_to_blocks(blocks, _MAP), generate=always_bad, max_text_attempts=2
    )
    assert calls["n"] == 2  # exactly the cap, no runaway loop
