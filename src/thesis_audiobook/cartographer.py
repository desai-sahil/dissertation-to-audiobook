"""Pure core for the thesis cartographer: build a structural "mental map" of the doc.

The cartographer is the deterministic, claim-safe half of the structure-evaluator stage
(the effectful, cached half is stages/cartographer.py, mirroring curate). The LLM returns
ONLY a StructureMap: enums, confidences, and back-pointers to EXISTING block ids. It never
authors spoken text. `apply_map` renders those labels deterministically onto block types,
so the existing select stage decides keep/handling unchanged. This module does no I/O.

Claim-safety: the model cannot inject audio because no field it returns is ever spoken
(`label`/`rationale` appear only in the structure.md artifact), and `apply_map` validates
every block id against the real document, dropping any region that references a phantom id
or inverts its span. The worst a misclassification can do is change WHETHER a verbatim
region is spoken - and every spoken->skip demotion is surfaced as a warning, never silent.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from thesis_audiobook.cleanup import classify_block
from thesis_audiobook.ir import (
    Block,
    BlockType,
    Document,
    Region,
    RegionDecision,
    RegionKind,
    StructureMap,
)
from thesis_audiobook.warnings import LowConfidence

CARTOGRAPHER_VERSION = "cartographer-v2"
CARTOGRAPHER_SYSTEM = (
    "You are a careful document-structure analyst for an audiobook pipeline. Classify and "
    "bound regions only; never rewrite, summarize, or author content. Return ONLY the JSON "
    "object requested - no prose, no markdown code fences."
)
# A full thesis can have dozens of regions; a small (gloss-sized) cap would truncate the
# JSON into garbage. Output is billed per actual token, so a generous cap is free unless used.
CARTOGRAPHER_MAX_TOKENS = 16_384

# Above this kind-confidence a heading-anchored region applies without a warning.
AUTO_APPLY_CONFIDENCE = 0.85
# A defensive ceiling on the outline handed to the model; over this the stage warns
# rather than silently sending a truncated map of a very long thesis.
OUTLINE_CHAR_CEILING = 120_000

# kind -> what each block in the region becomes. SPOKEN kinds are special-cased in
# apply_map (they re-derive type per block to preserve headings/tables/equations).
_SPOKEN_KINDS = frozenset(
    {
        RegionKind.abstract,
        RegionKind.biographical_sketch,
        RegionKind.dedication,
        RegionKind.epigraph,
        RegionKind.acknowledgments,
        RegionKind.preface_or_foreword,
        RegionKind.chapter_body,
        RegionKind.chapter_abstract,
    }
)
_FRONTMATTER_KINDS = frozenset(
    {
        RegionKind.title_page,
        RegionKind.copyright_page,
        RegionKind.table_of_contents,
        RegionKind.list_of_tables,
        RegionKind.list_of_figures,
        RegionKind.list_of_abbreviations,
        RegionKind.chapter_front_note,
    }
)
_REFERENCE_KINDS = frozenset(
    {
        RegionKind.per_chapter_bibliography,
        RegionKind.bibliography,
        RegionKind.appendix_bibliography,
    }
)
_BACKMATTER_KINDS = frozenset(
    {
        RegionKind.appendix,
        RegionKind.supplementary_information,
        RegionKind.glossary,
        RegionKind.index_section,
        RegionKind.colophon_or_vita,
    }
)

# A block ending up one of these is excluded from audio by the select stage.
_SKIP_TYPES = frozenset(
    {BlockType.frontmatter, BlockType.backmatter, BlockType.reference_list, BlockType.footnote}
)
_PROSE_TYPES = frozenset({BlockType.heading, BlockType.paragraph})


def effective_decision(kind: RegionKind, include_appendices: bool) -> str:
    """The decision that actually takes effect, derived from kind + profile (NOT the LLM's
    advisory `decision` field). This is what the select stage will do, so the review map
    shows the real outcome: spoken kinds are kept; appendices/SI ride include_appendices;
    front matter, reference lists and footnotes are skipped; unknown routes to review.
    """
    if kind in _SPOKEN_KINDS:
        return "include"
    if kind in _BACKMATTER_KINDS:
        return "include" if include_appendices else "skip"
    if kind is RegionKind.unknown:
        return "review"
    return "skip"


def _norm(text: str) -> str:
    return " ".join(text.split())


# How many block lines to show at the head/tail of a long same-class run before summarizing
# the middle. The head window must be wide enough to expose unlabeled front matter (the
# abstract sits a few blocks in, after the title/copyright).
_RUN_HEAD = 8
_RUN_TAIL = 1


def _effective_type(block: Block) -> BlockType:
    """The structural type to SHOW the cartographer.

    build_ir's one-way latch buries everything after the first references heading as
    `backmatter`, which would hide chapters 2..N in a single featureless blob. For the
    outline we re-derive the real type from the text (CHAPTER/section headings, [n]
    reference entries) so the model can see and partition the true structure. apply_map
    then re-derives those same blocks back to prose for any region kept as chapter_body.
    """
    if block.type in (BlockType.backmatter, BlockType.frontmatter):
        return classify_block(block.text)
    return block.type


def _outline_class(block_type: BlockType) -> str:
    """Coarse class used to group runs in the outline while preserving boundaries."""
    if block_type is BlockType.heading:
        return "heading"
    if block_type is BlockType.reference_list:
        return "ref"
    return "body"


def _page_span(blocks: list[Block]) -> str:
    pages = [b.page for b in blocks if b.page is not None]
    if not pages:
        return "p?"
    lo, hi = min(pages), max(pages)
    return f"p{lo}" if lo == hi else f"p{lo}-{hi}"


def _histogram(types: list[BlockType]) -> str:
    counts: dict[str, int] = {}
    for t in types:
        counts[t.value] = counts.get(t.value, 0) + 1
    return ",".join(f"{name}x{counts[name]}" for name in sorted(counts))


def _heading_line(block: Block, eff: BlockType) -> str:
    ch = block.chapter if block.chapter is not None else "-"
    return (
        f"{block.id} | {_page_span([block])} | {eff.value} | ch{ch}"
        f" | sec:{block.section or '-'} | {_norm(block.text)[:120]}"
    )


def _block_line(block: Block, eff: BlockType) -> str:
    return f"{block.id} | {_page_span([block])} | {eff.value} | {_norm(block.text)[:100]}"


def _run_lines(run: list[Block], types: list[BlockType]) -> list[str]:
    """Per-block lines for a run, with the middle of a long run summarized to bound tokens.

    Showing the first few blocks individually is what lets the model separate unlabeled
    front matter (title vs copyright vs abstract) that has no headings between blocks.
    """
    if len(run) <= _RUN_HEAD + _RUN_TAIL + 1:
        return [_block_line(b, t) for b, t in zip(run, types, strict=True)]
    head = [_block_line(run[k], types[k]) for k in range(_RUN_HEAD)]
    mid_types = types[_RUN_HEAD : len(run) - _RUN_TAIL]
    summary = f"  ...(+{len(mid_types)} more blocks: {_histogram(mid_types)})"
    tail = [_block_line(run[k], types[k]) for k in range(len(run) - _RUN_TAIL, len(run))]
    return [*head, summary, *tail]


def build_outline(doc: Document) -> str:
    """A compact, deterministic outline for the LLM: every heading individually, and each
    run of same-class non-heading blocks shown per-block (head/tail) with the middle
    summarized. Types are the re-derived effective types, never the raw latched ones."""
    lines = [f"TITLE: {_norm(doc.meta.title)} | AUTHOR: {_norm(doc.meta.author or '')}"]
    blocks = doc.blocks
    types = [_effective_type(b) for b in blocks]
    i = 0
    n = len(blocks)
    while i < n:
        if types[i] is BlockType.heading:
            lines.append(_heading_line(blocks[i], types[i]))
            i += 1
            continue
        cls = _outline_class(types[i])
        j = i
        while j < n and types[j] is not BlockType.heading and _outline_class(types[j]) == cls:
            j += 1
        lines.extend(_run_lines(blocks[i:j], types[i:j]))
        i = j
    return "\n".join(lines)


def build_fingerprint(doc: Document) -> str:
    """A strong digest over the FULL ordered (id, type, normalized-text) sequence.

    Used for the cache key (NOT the lossy outline) so two distinct documents can never
    collide onto the same cached map.
    """
    parts = [f"{b.id}\t{b.type.value}\t{_norm(b.text)}" for b in doc.blocks]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def build_cartographer_prompt(outline: str, title: str, author: str | None) -> str:
    kinds = ", ".join(k.value for k in RegionKind)
    return (
        "You are a meticulous human evaluator mapping the STRUCTURE of a PhD thesis so it "
        "can be turned into an audiobook. You are given a compact outline of the document: "
        "one line per heading and one line per collapsed run of body/reference/front/back "
        "blocks. A heading line starts with a single block id (e.g. 'b53'); a run line starts "
        "with an id RANGE 'bFIRST..bLAST' (e.g. 'b54..b119') meaning that run spans blocks "
        "b54 through b119 inclusive. Use only real endpoint ids like 'b54' or 'b119' for "
        "region boundaries - never the literal range string 'b54..b119'. Every block id in "
        "the document must fall inside exactly one region (full, gapless coverage).\n\n"
        'Return ONLY a JSON object of the form {"title": ..., "author": ..., "regions": [ ... ]}.\n'
        "title/author: the DISSERTATION's actual title and author, copied VERBATIM from the "
        "title-page region (not a chapter title), or null if unclear.\n"
        "Partition the document into contiguous, NON-overlapping regions in reading order. "
        "For each region give:\n"
        f"  kind: one of [{kinds}]\n"
        "  decision: one of [include, skip, review]\n"
        "  first_block_id / last_block_id: existing block ids from the outline (inclusive)\n"
        "  chapter: the owning chapter number, or null\n"
        "  label: a short heading COPIED VERBATIM from the outline (do not invent text)\n"
        "  heading_anchored: true iff first_block_id is a heading line in the outline\n"
        "  kind_confidence / decision_confidence: floats in [0,1]\n"
        "  rationale: one short clause (shown only to the human reviewer, never spoken)\n"
        "  duplicate_of: first_block_id of a region this duplicates (e.g. a repeated or "
        "translated abstract), else null\n"
        "  language: ISO code if this region is NOT the document's primary language, else null\n\n"
        "Rules: Classify and bound ONLY. Do NOT rewrite, summarize, translate, or author any "
        "text. A stapled-papers thesis has a SEPARATE bibliography after EACH chapter and EACH "
        "appendix - scope every reference list to its own chapter/appendix, never let one "
        "'References' heading swallow the rest of the document. The abstract may be UNLABELED "
        "(it opens by repeating the title). Appendices are supplemental. Mark anything you are "
        "unsure about decision=review with an honest low confidence.\n\n"
        f"TITLE: {title}\nAUTHOR: {author or ''}\n\nOUTLINE:\n{outline}\n"
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3]
    start = text.find("{")
    end = text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else ""


def parse_map(raw: str) -> StructureMap:
    """Parse the model's JSON into a StructureMap; return an EMPTY map on ANY failure.

    So the offline mock's non-JSON response degrades to a strict no-op, exactly like the
    curator's parse_plan.
    """
    payload = _strip_fences(raw)
    if not payload:
        return StructureMap()
    try:
        data: Any = json.loads(payload)
        return StructureMap.model_validate(data)
    except Exception:
        return StructureMap()


def _region_warnings(region: Region) -> list[LowConfidence]:
    out: list[LowConfidence] = []
    k = region.kind.value
    score = min(region.kind_confidence, region.decision_confidence)

    def warn(reason: str, s: float) -> None:
        out.append(LowConfidence(block_id=region.first_block_id, reason=reason, score=s))

    if region.kind is RegionKind.unknown:
        warn(f"cartographer: unclassified region (label {region.label!r}); review", score)
    if region.decision is RegionDecision.review:
        warn(f"cartographer: {k} flagged for review - {region.rationale}", score)
    if region.kind_confidence < AUTO_APPLY_CONFIDENCE:
        warn(
            f"cartographer: low confidence on {k} ({region.kind_confidence:.2f})",
            region.kind_confidence,
        )
    if region.kind in _SPOKEN_KINDS and not region.heading_anchored:
        warn(
            f"cartographer: kept {k} on an UNLABELED span (boundary unverifiable)",
            region.kind_confidence,
        )
    if region.duplicate_of is not None:
        warn(f"cartographer: {k} looks like a duplicate of {region.duplicate_of}", score)
    if region.language is not None:
        warn(f"cartographer: {k} appears to be in '{region.language}' (non-primary)", score)
    return out


def _apply_region(region: Region, span: list[Block]) -> list[LowConfidence]:
    warnings: list[LowConfidence] = []
    for block in span:
        before = block.type
        if region.kind in _SPOKEN_KINDS:
            # Un-skip prose the build_ir latch/parser wrongly buried, but preserve real
            # structure (headings, tables, equations, captions) by re-deriving from text.
            # reference_list blocks are deliberately NOT touched here, so numbered "[n]"
            # bibliographies stay skipped even if the model mislabels their region as a
            # chapter body. (Residual: an author-year reference run that build_ir latched as
            # backmatter re-derives to paragraph and would be spoken if mislabeled - rare,
            # and not the case for numbered-citation theses.)
            if block.type in (BlockType.frontmatter, BlockType.backmatter):
                block.type = classify_block(block.text)
        elif region.kind in _FRONTMATTER_KINDS:
            block.type = BlockType.frontmatter
        elif region.kind in _REFERENCE_KINDS:
            block.type = BlockType.reference_list
        elif region.kind in _BACKMATTER_KINDS:
            block.type = BlockType.backmatter
        elif region.kind is RegionKind.footnotes:
            block.type = BlockType.footnote
        # RegionKind.unknown: leave the block type untouched.

        # Silent-deletion guard: never demote real prose to a skipped type unflagged.
        if before in _PROSE_TYPES and block.type in _SKIP_TYPES:
            warnings.append(
                LowConfidence(
                    block_id=block.id,
                    reason=(
                        f"cartographer: demoted spoken {before.value} to {block.type.value} "
                        f"in region {region.kind.value}"
                    ),
                    score=region.kind_confidence,
                )
            )
        # Fill chapter when missing; never silently renumber an existing chapter.
        if region.chapter is not None:
            if block.chapter is None:
                block.chapter = region.chapter
            elif block.chapter != region.chapter:
                warnings.append(
                    LowConfidence(
                        block_id=block.id,
                        reason=(
                            f"cartographer: region says chapter {region.chapter} but block is "
                            f"chapter {block.chapter}; kept block value"
                        ),
                        score=region.decision_confidence,
                    )
                )
    if span:
        span[0].notes.append(
            f"cartographer: {region.kind.value}/{region.decision.value} "
            f"kc={region.kind_confidence:.2f} dc={region.decision_confidence:.2f}"
        )
    return warnings


def _apply_metadata(doc: Document, smap: StructureMap, warnings: list[LowConfidence]) -> None:
    """Adopt the cartographer's title/author ONLY if found verbatim in the document.

    The title is spoken in the assemble_script intro, so this stays claim-safe: the model
    cannot fabricate a title - it must already appear (normalized) somewhere in the source.
    """
    sentinel = doc.blocks[0].id if doc.blocks else "document"
    haystack = _norm(" ".join(b.text for b in doc.blocks)).lower()

    def adopt(value: str | None, field: str) -> str | None:
        candidate = (value or "").strip()
        if not candidate:
            return None
        if _norm(candidate).lower() in haystack:
            return candidate
        warnings.append(
            LowConfidence(
                block_id=sentinel,
                reason=f"cartographer: proposed {field} not found verbatim; kept existing",
                score=0.3,
            )
        )
        return None

    title = adopt(smap.title, "title")
    if title is not None:
        doc.meta.title = title
    author = adopt(smap.author, "author")
    if author is not None:
        doc.meta.author = author


def apply_map(doc: Document, structure_map: StructureMap) -> list[LowConfidence]:
    """Deterministically render the structure map onto block types. Mutates doc.blocks;
    returns the warnings to add to the sink. Never touches block.text or block.spoken.

    Empty map => strict no-op (no mutations, no warnings) so the offline mock is inert.
    """
    if structure_map.is_empty():
        return []

    warnings: list[LowConfidence] = []
    _apply_metadata(doc, structure_map, warnings)

    index_of = {b.id: i for i, b in enumerate(doc.blocks)}
    spans: list[tuple[int, int, Region]] = []
    for region in structure_map.regions:
        fi = index_of.get(region.first_block_id)
        li = index_of.get(region.last_block_id)
        if fi is None or li is None or fi > li:
            warnings.append(
                LowConfidence(
                    block_id=region.first_block_id,
                    reason=f"cartographer: dropped region with bad span ({region.kind.value})",
                    score=0.0,
                )
            )
            continue
        spans.append((fi, li, region))
    spans.sort(key=lambda s: s[0])

    covered: set[str] = set()
    last_used = -1
    for fi, li, region in spans:
        if fi <= last_used:
            warnings.append(
                LowConfidence(
                    block_id=region.first_block_id,
                    reason=f"cartographer: dropped overlapping region ({region.kind.value})",
                    score=0.0,
                )
            )
            continue
        span = doc.blocks[fi : li + 1]
        warnings.extend(_apply_region(region, span))
        warnings.extend(_region_warnings(region))
        covered.update(b.id for b in span)
        last_used = li

    # Coverage guard: a block left out of every region keeps its build_ir type; if that
    # type is skipped yet the text reads like prose, it may be content silently dropped.
    skip_matter = (BlockType.frontmatter, BlockType.backmatter)
    for block in doc.blocks:
        uncovered_skip = block.id not in covered and block.type in skip_matter
        if uncovered_skip and classify_block(block.text) in _PROSE_TYPES:
            warnings.append(
                LowConfidence(
                    block_id=block.id,
                    reason=(
                        f"cartographer: block left {block.type.value} (skipped) but text reads "
                        "like prose; not covered by any region"
                    ),
                    score=0.4,
                )
            )
    return warnings


def render_structure_md(
    structure_map: StructureMap, doc: Document, *, include_appendices: bool = False
) -> str:
    """Human-readable map for the pre-spend review (written to out/<slug>.structure.md).

    The Decision column is the EFFECTIVE outcome (kind + include_appendices) for every
    classified kind - not the model's advisory `decision` field, which can disagree (e.g.
    the model may suggest skipping the biographical sketch, but the profile keeps it). A
    "review" decision means the region is `unknown`/unclassified: apply_map leaves those
    blocks at their extracted type and flags them, so they are NOT auto-held - they may
    still be spoken. Such rows always carry an "unknown" flag for a human check.
    """
    lines = ["# Thesis structure map (LLM cartographer)", ""]
    if structure_map.is_empty():
        lines.append("Cartographer returned no map (offline mock, or disabled).")
        return "\n".join(lines) + "\n"

    def cell(value: str) -> str:
        return value.replace("|", "\\|")

    lines += [
        "| Region | Chapter | Decision | Kind-conf | Dec-conf | Blocks | Flags |",
        "|---|---|---|---|---|---|---|",
    ]
    flagged: list[Region] = []
    for r in structure_map.regions:
        flags: list[str] = []
        if r.decision is RegionDecision.review:
            flags.append("review")
        if r.kind_confidence < AUTO_APPLY_CONFIDENCE:
            flags.append("low-conf")
        if r.duplicate_of is not None:
            flags.append("duplicate")
        if r.language is not None:
            flags.append(f"lang:{r.language}")
        if r.kind in _SPOKEN_KINDS and not r.heading_anchored:
            flags.append("unlabeled")
        if r.kind is RegionKind.unknown:
            flags.append("unknown")
        if flags:
            flagged.append(r)
        ch = r.chapter if r.chapter is not None else "-"
        decision = effective_decision(r.kind, include_appendices)
        lines.append(
            f"| {cell(r.kind.value)} ({cell(r.label)}) | {ch} "
            f"| {decision} | {r.kind_confidence:.2f} | {r.decision_confidence:.2f} "
            f"| {cell(r.first_block_id)}..{cell(r.last_block_id)} | {', '.join(flags) or '-'} |"
        )

    if flagged:
        lines += ["", "## Flagged for review", ""]
        for r in flagged:
            lines.append(f"- **{cell(r.kind.value)}** ({cell(r.label)}): {cell(r.rationale)}")
    return "\n".join(lines) + "\n"
