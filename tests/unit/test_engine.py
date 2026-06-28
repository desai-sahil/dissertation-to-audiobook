from __future__ import annotations

from thesis_audiobook.engine import (
    map_structure_to_blocks,
    narrate_document,
)
from thesis_audiobook.ir import Block, BlockType
from thesis_audiobook.vision_structure import VisionSection, VisionStructureMap


def _block(bid: str, page: int, text: str, btype: BlockType = BlockType.paragraph) -> Block:
    return Block(id=bid, type=btype, page=page, text=text)


_MAP = VisionStructureMap(
    sections=[
        VisionSection(number="", title="Abstract", start_page=3, kind="abstract"),
        VisionSection(number="I", title="INTRODUCTION", start_page=5, kind="body_chapter"),
        VisionSection(number="II", title="BACKGROUND", start_page=10, kind="body_chapter"),
        VisionSection(number="VII", title="REFERENCES", start_page=20, kind="references"),
    ]
)


def _doc_blocks() -> list[Block]:
    return [
        _block("title", 1, "Title page material"),  # before any section -> review
        _block("abs", 3, "Abstract reports 0.5 units"),  # read (front matter)
        _block("h1", 5, "I. INTRODUCTION", BlockType.heading),  # read heading -> announced
        _block("p1", 6, "increased by 0.5 units"),  # read prose -> narrate (ok)
        _block("p2", 11, "decreased by 0.9"),  # read prose -> narrate (fails -> held)
        _block("ref", 21, "[1] Smith et al."),  # references -> skip
    ]


def _fake_generate(prompt: str) -> str:
    # keyed off the source embedded in the prompt; p2's reply changes the value (verifier fails)
    if "Abstract reports 0.5 units" in prompt:
        return "Abstract reports zero point five units"
    if "increased by 0.5 units" in prompt:
        return "increased by zero point five units"
    if "decreased by 0.9" in prompt:
        return "decreased by zero point one"  # 0.9 -> 0.1: value changed
    return "ok"


def test_map_assigns_decision_kind_and_chapter_by_page() -> None:
    a = map_structure_to_blocks(_doc_blocks(), _MAP)
    assert a["title"].decision == "review" and a["title"].kind == "unmapped"
    assert a["abs"].decision == "read" and a["abs"].kind == "abstract" and a["abs"].chapter is None
    assert a["h1"].decision == "read" and a["h1"].chapter == 1
    assert a["p1"].chapter == 1
    assert a["p2"].chapter == 2  # second body chapter
    assert a["ref"].decision == "skip" and a["ref"].kind == "references"


def test_narrate_document_routes_each_block() -> None:
    blocks = _doc_blocks()
    by_id = {b.id: b for b in blocks}
    assignments = map_structure_to_blocks(blocks, _MAP)
    outcome = narrate_document(blocks, assignments, generate=_fake_generate)

    # read prose, verified -> spoken set, shipped
    assert by_id["p1"].spoken == "increased by zero point five units" and by_id["p1"].keep
    assert by_id["abs"].spoken and by_id["abs"].keep
    # heading -> kept for assemble to announce, not narrated, chapter set
    assert by_id["h1"].keep and by_id["h1"].spoken is None and by_id["h1"].chapter == 1
    # references -> skipped
    assert by_id["ref"].keep is False
    # before-first-section -> review, not shipped
    assert by_id["title"].keep is False
    # verifier-failed narration -> NOT shipped (claim safety)
    assert by_id["p2"].keep is False

    assert outcome.narrated == 2 and outcome.held == 1
    assert outcome.skipped == 1 and outcome.reviewed == 1
    assert len(outcome.pairs) == 3  # abs, p1, p2 all attempted
    reasons = {f.block_id: f.reason for f in outcome.flagged}
    assert reasons == {"title": "review", "p2": "verifier"}
    assert any(
        v.kind == "values" for f in outcome.flagged if f.block_id == "p2" for v in f.violations
    )


def test_narration_is_bounded_per_block() -> None:
    # cost safety: a block that never verifies makes at most max_text_attempts calls, then stops.
    calls = {"n": 0}

    def always_bad(_prompt: str) -> str:
        calls["n"] += 1
        return "decreased by zero point one"  # never satisfies 0.9

    blocks = [_block("p", 11, "decreased by 0.9")]
    narrate_document(
        blocks, map_structure_to_blocks(blocks, _MAP), generate=always_bad, max_text_attempts=2
    )
    assert calls["n"] == 2  # exactly the cap, no runaway loop
