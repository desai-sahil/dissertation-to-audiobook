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
from concurrent.futures import ThreadPoolExecutor

from thesis_audiobook.ir import Block, BlockType, StrictModel
from thesis_audiobook.narrate import NarrationResult, narrate_segment
from thesis_audiobook.verifier import Violation
from thesis_audiobook.vision_structure import VisionStructureMap, section_decision

# Prose kinds the narrator voices. Headings are announced deterministically by assemble_script;
# figures/tables/equations/references are not narrated in this first v2 cut (refined later).
NARRATABLE_TYPES = frozenset({BlockType.paragraph, BlockType.frontmatter})


class BlockAssignment(StrictModel):
    decision: str  # read | skip | review
    kind: str  # the governing section's kind, or "unmapped"
    chapter: int | None  # 1-based body-chapter index when in a body chapter, else None
    section_head: bool = False  # this heading is the section's start (matched a vision section)


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
    narrated: int = 0  # prose shipped (passed the verifier)
    announced: int = 0  # equations/tables announced deterministically (bypass the verifier)
    held: int = 0  # narrated but failed the verifier -> not shipped
    skipped: int = 0
    reviewed: int = 0  # unmapped / review-kind -> not shipped, surfaced


_ENUMERATOR = re.compile(r"^(?:[IVXLCDM]+|\d+)(?:\.[A-Za-z0-9]+)*\.?\s+")


def strip_heading_enumerator(text: str) -> str:
    """Drop a leading heading enumerator ('I.', 'III.A.1.', '2.3'), leaving only the title words."""
    stripped = _ENUMERATOR.sub("", text).strip()
    return stripped or text


REVIEW_RATE_GATE = 0.15  # above this fraction held-or-for-review, recommend human review


def review_gate(outcome: EngineOutcome) -> str | None:
    """Confidence-gated escalation: if too many segments were held by the verifier or routed to
    review, recommend a human look rather than shipping confidently-incomplete audio. Returns the
    reason, or None if within tolerance."""
    total = outcome.narrated + outcome.announced + outcome.held + outcome.reviewed
    if total == 0:
        return "nothing was narrated"
    flagged = outcome.held + outcome.reviewed
    rate = flagged / total
    if rate > REVIEW_RATE_GATE:
        return f"{flagged}/{total} segments held or flagged for review ({rate:.0%})"
    return None


def _heading_key(text: str) -> str:
    """A comparable key from a heading's TITLE: drop a leading enumerator, lowercase, collapse
    non-alphanumeric. So 'I. INTRODUCTION' and 'INTRODUCTION' both -> 'introduction' - matching on
    the title (not the number) is what bridges Zhu (number in the heading text) and Gao (number is a
    separate 'CHAPTER N' divider the IR strips, and vision's number field is noisy)."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", strip_heading_enumerator(text).lower()).split())


def map_structure_to_blocks(
    blocks: list[Block], structure_map: VisionStructureMap
) -> dict[str, BlockAssignment]:
    """Anchor the vision sections to the IR's own heading blocks (robust to vision's page-number
    drift and noisy numbering). Each top-level vision section is matched to the heading whose TITLE
    it labels; its read/skip decision then propagates, in document order, to that heading and the
    blocks under it until the next matched section. Blocks before the first match are 'review'
    (never silently read or dropped). Body chapters get a 1-based index in section order."""
    ordered: list[tuple[str, str, int | None]] = []  # (title key, kind, chapter), in section order
    chapter_no = 0
    for section in structure_map.sections:
        chapter: int | None = None
        if section.kind.strip().lower() == "body_chapter":
            chapter_no += 1
            chapter = chapter_no
        key = _heading_key(section.title)  # match on the title; vision's number field is unreliable
        if key:
            ordered.append((key, section.kind, chapter))

    # Ordered, one-to-one matching: walk the sections and headings together, consuming each section
    # at most once. A later heading whose title repeats an already-consumed section (a chapter's own
    # "Conclusion"/"Introduction" subsection) cannot re-match it, so it stays a subsection and does
    # not trigger a duplicate "Chapter N".
    result: dict[str, BlockAssignment] = {}
    cur_decision, cur_kind = "review", "unmapped"
    cur_chapter: int | None = None
    next_idx = 0
    for block in blocks:
        is_section_head = False
        if block.type is BlockType.heading:
            hkey = _heading_key(block.text)
            for j in range(next_idx, len(ordered)):
                if ordered[j][0] == hkey:
                    _, cur_kind, cur_chapter = ordered[j]
                    cur_decision = section_decision(cur_kind)
                    is_section_head = True
                    next_idx = j + 1
                    break
        result[block.id] = BlockAssignment(
            decision=cur_decision, kind=cur_kind, chapter=cur_chapter, section_head=is_section_head
        )
    return result


def narrate_document(
    blocks: list[Block],
    assignments: dict[str, BlockAssignment],
    *,
    generate: Callable[[str], str],
    announce: Callable[[Block], str | None] | None = None,
    vision_for: Callable[[Block], Callable[[str], str] | None] | None = None,
    max_text_attempts: int = 2,
    max_workers: int = 1,
) -> EngineOutcome:
    """Narrate the read prose blocks in place; announce/skip the rest. `generate` is the text model;
    `announce(block)` returns a deterministic announcement for a non-prose block (equation/table) or
    None to skip it - announcements BYPASS the verifier, since they deliberately omit the source's
    symbols. `vision_for(block)` optionally returns a per-block vision generator for escalation.

    The per-block narrations are INDEPENDENT, so with max_workers > 1 they run concurrently and the
    results are applied in document order - output is byte-identical to the sequential path, only
    faster (each narrate_segment is still hard-capped, so total calls stay bounded)."""
    outcome = EngineOutcome()
    to_narrate: list[Block] = []
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
            block.keep = True
            if not assignment.section_head:
                # a subsection heading: announce its bare title (not "Chapter N" again) and let it
                # fold into the chapter audio (chapter=None is forward-filled downstream).
                block.chapter = None
            continue
        if block.type not in NARRATABLE_TYPES or not block.text.strip():
            # non-prose (equation/table/figure): announce deterministically if the hook handles it,
            # else skip. Announcements bypass the verifier (they omit the source's symbols).
            announcement = announce(block) if announce is not None else None
            if announcement:
                block.spoken = announcement
                block.keep = True
                outcome.announced += 1
            else:
                block.keep = False
                outcome.skipped += 1
            continue
        to_narrate.append(block)

    def _narrate(block: Block) -> NarrationResult:
        vision_generate = vision_for(block) if vision_for is not None else None
        return narrate_segment(
            block.text,
            generate=generate,
            vision_generate=vision_generate,
            max_text_attempts=max_text_attempts,
        )

    if max_workers > 1 and len(to_narrate) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            results = list(pool.map(_narrate, to_narrate))  # map preserves input order
    else:
        results = [_narrate(block) for block in to_narrate]

    for block, result in zip(to_narrate, results, strict=True):
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
