"""The v2 engine (phase D2): drive a Document from the vision structure map to spoken blocks.

Given the ingested IR blocks and the vision structure map, this maps each block to its governing
section (by page), applies the read/skip policy, and narrates each READ prose block through the
verifier-gated generator. It mutates blocks in place (sets spoken / keep / chapter, the pipeline
convention) and returns the (source, spoken) pairs for faithfulness scoring plus anything flagged
for human review.

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


def map_structure_to_blocks(
    blocks: list[Block], structure_map: VisionStructureMap
) -> dict[str, BlockAssignment]:
    """Assign each block its governing section's decision/kind and (for body chapters) a 1-based
    chapter index, by page. A block before the first section or with no page is 'review' (never
    silently read or dropped)."""
    ordered = sorted(
        structure_map.sections, key=lambda s: (s.start_page is None, s.start_page or 0)
    )
    annotated: list[tuple[int | None, str, int | None]] = []  # (start_page, kind, chapter_index)
    chapter_no = 0
    for section in ordered:
        if section.kind.strip().lower() == "body_chapter":
            chapter_no += 1
            annotated.append((section.start_page, section.kind, chapter_no))
        else:
            annotated.append((section.start_page, section.kind, None))

    result: dict[str, BlockAssignment] = {}
    for block in blocks:
        gov_kind = "unmapped"
        gov_chapter: int | None = None
        if block.page is not None:
            for start_page, kind, chapter in annotated:
                if start_page is None:
                    continue
                if start_page <= block.page:
                    gov_kind, gov_chapter = kind, chapter
                else:
                    break  # ordered ascending: no later section can govern this page
        decision = section_decision(gov_kind) if gov_kind != "unmapped" else "review"
        result[block.id] = BlockAssignment(decision=decision, kind=gov_kind, chapter=gov_chapter)
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
