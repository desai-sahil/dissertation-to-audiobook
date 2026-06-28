"""The v2 engine (phase D2): drive a Document from the vision structure map to spoken blocks.

Given the ingested IR blocks and the vision structure map, this anchors each vision section to the
IR's own heading blocks (the boundaries) while taking each section's read/skip KIND from vision (the
semantics), applies the policy, and narrates each READ prose block through the verifier-gated
generator. Heading-anchoring is deliberate: vision's page-number estimates drift on later pages, but
the printed heading text it labels is exact. It mutates blocks in place (sets spoken / keep /
chapter, the pipeline convention) and returns the (source, spoken) pairs for faithfulness scoring
plus anything flagged for human review.

COST SAFETY (by construction, not by luck):
  - It walks a FINITE block list exactly ONCE - no re-queue, no while-loop.
  - Each block is narrated by narrate_segment, itself hard-capped (<= max_text_attempts text calls
    + <= 1 vision call). So total model calls <= blocks * (max_text_attempts + 1), bounded.
  - A block that fails the verifier after its attempts is NOT shipped (keep=False) and flagged for
    review, so unverified narration never reaches the audio.
  - generate/vision_generate are injected; the stage wraps them with the content-addressed cache, so
    a re-run re-bills nothing and a single edit re-narrates only the changed block.

Pure: no I/O, no SDK; the model callables are injected by the stage.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from thesis_audiobook.ir import Block, BlockType, StrictModel
from thesis_audiobook.narrate import narrate_segment
from thesis_audiobook.verifier import Violation
from thesis_audiobook.vision_structure import VisionStructureMap, section_decision

# Prose kinds the narrator voices. Headings are announced deterministically by assemble_script;
# figures/tables/equations/references are not narrated in this first v2 cut (refined later).
NARRATABLE_TYPES = frozenset({BlockType.paragraph, BlockType.frontmatter})


class BlockAssignment(StrictModel):
    decision: str  # read | skip | review
    kind: str  # the governing section's kind, or "unmapped"
    chapter: int | None  # 1-based body-chapter index when in a body chapter, else None


class SegmentPair(StrictModel):
    block_id: str
    source: str
    spoken: str


class FlaggedSegment(StrictModel):
    block_id: str
    reason: str  # "review" (unmapped / review-kind) or "verifier" (narration failed the floor)
    violations: list[Violation] = []


class EngineOutcome(StrictModel):
    pairs: list[SegmentPair] = []  # every attempted narration (ok or not) for faithfulness scoring
    flagged: list[FlaggedSegment] = []
    narrated: int = 0  # shipped (passed the verifier)
    held: int = 0  # narrated but failed the verifier -> not shipped
    skipped: int = 0
    reviewed: int = 0  # unmapped / review-kind -> not shipped, surfaced


def _heading_key(text: str) -> str:
    """Normalize a heading (or a vision section's number + title) to a comparable key: lowercase,
    non-alphanumeric collapsed to spaces. 'VII. REFERENCES' and 'VII REFERENCES' both -> 'vii
    references'; a subsection 'III.A. ...' -> 'iii a ...' won't collide with chapter 'iii ...'."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def map_structure_to_blocks(
    blocks: list[Block], structure_map: VisionStructureMap
) -> dict[str, BlockAssignment]:
    """Anchor the vision sections to the IR's own heading blocks (robust to vision's page-number
    drift). Each top-level vision section is matched to the heading whose printed text it labels;
    its read/skip decision then propagates, in document order, to that heading and the blocks under
    it until the next matched section. Blocks before the first match are 'review' (never silently
    read or dropped). A 1-based chapter index is assigned to body chapters in section order."""
    section_by_key: dict[str, tuple[str, int | None]] = {}
    chapter_no = 0
    for section in structure_map.sections:
        chapter: int | None = None
        if section.kind.strip().lower() == "body_chapter":
            chapter_no += 1
            chapter = chapter_no
        key = _heading_key(f"{section.number} {section.title}")
        if key:
            section_by_key[key] = (section.kind, chapter)

    result: dict[str, BlockAssignment] = {}
    cur_decision, cur_kind = "review", "unmapped"
    cur_chapter: int | None = None
    for block in blocks:
        if block.type is BlockType.heading:
            hit = section_by_key.get(_heading_key(block.text))
            if hit is not None:
                cur_kind, cur_chapter = hit
                cur_decision = section_decision(cur_kind)
        result[block.id] = BlockAssignment(
            decision=cur_decision, kind=cur_kind, chapter=cur_chapter
        )
    return result


def narrate_document(
    blocks: list[Block],
    assignments: dict[str, BlockAssignment],
    *,
    generate: Callable[[str], str],
    vision_for: Callable[[Block], Callable[[str], str] | None] | None = None,
    max_text_attempts: int = 2,
) -> EngineOutcome:
    """Narrate the read prose blocks in place; skip the rest. Bounded and single-pass (see module
    docs). `generate` is the text model; `vision_for(block)` optionally returns a per-block vision
    generator for escalation (None = text-only, the first-cut default)."""
    outcome = EngineOutcome()
    for block in blocks:
        assignment = assignments.get(block.id)
        if assignment is None:
            assignment = BlockAssignment(decision="review", kind="unmapped", chapter=None)
        if assignment.chapter is not None:
            block.chapter = assignment.chapter

        if assignment.decision == "skip":
            block.keep = False
            outcome.skipped += 1
            continue
        if assignment.decision == "review":
            block.keep = False
            outcome.reviewed += 1
            outcome.flagged.append(FlaggedSegment(block_id=block.id, reason="review"))
            continue

        # decision == read
        if block.type is BlockType.heading:
            block.keep = True  # assemble_script announces the heading deterministically
            continue
        if block.type not in NARRATABLE_TYPES or not block.text.strip():
            block.keep = False  # non-prose in a read section: not narrated in this cut
            outcome.skipped += 1
            continue

        vision_generate = vision_for(block) if vision_for is not None else None
        result = narrate_segment(
            block.text,
            generate=generate,
            vision_generate=vision_generate,
            max_text_attempts=max_text_attempts,
        )
        outcome.pairs.append(
            SegmentPair(block_id=block.id, source=block.text, spoken=result.spoken)
        )
        if result.ok:
            block.spoken = result.spoken
            block.keep = True
            outcome.narrated += 1
        else:
            block.keep = False  # never ship narration that failed the faithfulness floor
            outcome.held += 1
            outcome.flagged.append(
                FlaggedSegment(block_id=block.id, reason="verifier", violations=result.violations)
            )
    return outcome
