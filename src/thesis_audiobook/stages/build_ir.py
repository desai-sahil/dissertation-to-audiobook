"""Stage: build the canonical IR and clean PDF-extraction artifacts. Pure, no I/O.

Operates on the raw Document emitted by a parser adapter:
  - de-hyphenate, normalize ligatures, flatten line breaks;
  - rejoin tokens the extractor space-splits ("g s" -> "gs", "H2 O2" -> "H2O2");
  - strip bare page numbers and running headers/footers;
  - rejoin words and sentences split across a page break (with a Gate A warning, so
    the join is never silent);
  - refine block types; attach a section to each body block; merge wrapped-title
    fragments back into their heading; tag the References region as backmatter;
  - emit Gate A LowConfidence warnings for the judgment calls it makes.

Running build_ir on already-clean IR (the mock fixture) is a no-op.
"""

from __future__ import annotations

import re

from thesis_audiobook.cleanup import (
    classify_block,
    dehyphenate,
    detect_running_artifacts,
    ends_hyphenated,
    is_title_spillover,
    looks_like_page_number,
    normalize_ligatures,
    rejoin_split_tokens,
)
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document
from thesis_audiobook.normalization.latex import clean_markup
from thesis_audiobook.normalization.mojibake import fix_mojibake
from thesis_audiobook.normalization.repetition import collapse_repetition
from thesis_audiobook.warnings import LowConfidence

_BACKMATTER_HEADINGS = {"references", "bibliography"}
_TRAILING_WORD = re.compile(r"(\w+)[-­]$")


def _is_artifact(block: Block, running: set[str]) -> bool:
    text = block.text.strip()
    return looks_like_page_number(text) or (text in running and len(text) <= 60)


def _ends_sentence(text: str) -> bool:
    return text.rstrip().rstrip("”\"'").endswith((".", "!", "?"))


def _keeps_hyphen(text: str) -> bool:
    # A real compound (species-, guard-) keeps its hyphen; a syllable split (en-) drops it.
    match = _TRAILING_WORD.search(text.strip())
    return bool(match) and len(match.group(1)) >= 3


# Block types that can sit between a sentence and its continuation (a figure or table that
# interrupts the prose) without being part of it; the rejoin looks past them.
_INTERPOSABLE = {BlockType.figure_caption, BlockType.table}


def _last_paragraph_index(merged: list[Block]) -> int | None:
    """Index of the nearest preceding paragraph, looking past interposed figures/tables."""
    for k in range(len(merged) - 1, -1, -1):
        if merged[k].type is BlockType.paragraph:
            return k
        if merged[k].type not in _INTERPOSABLE:
            return None  # a heading/backmatter/etc. breaks the continuation
    return None


def _merge_cross_page_continuations(blocks: list[Block], ctx: Context) -> list[Block]:
    merged: list[Block] = []
    for block in blocks:
        if block.type is not BlockType.paragraph:
            merged.append(block)
            continue
        prev_idx = _last_paragraph_index(merged)
        if prev_idx is None:
            merged.append(block)
            continue
        previous = merged[prev_idx]
        interposed = prev_idx != len(merged) - 1  # a figure/table sits between the two
        if ends_hyphenated(previous.text) and not interposed:
            joined = previous.text.rstrip()
            previous.text = (joined if _keeps_hyphen(joined) else joined[:-1]) + block.text
            ctx.warnings.add(
                LowConfidence(
                    block_id=previous.id,
                    reason="joined a word split across a page break",
                    score=0.5,
                )
            )
            continue
        if not _ends_sentence(previous.text):
            # Across an interposed figure/table, only rejoin an obvious continuation (a
            # lower-case start), so a real new paragraph is not glued onto the previous one.
            if interposed and not block.text[:1].islower():
                merged.append(block)
                continue
            previous.text = f"{previous.text.rstrip()} {block.text.lstrip()}"
            if interposed:
                ctx.warnings.add(
                    LowConfidence(
                        block_id=previous.id,
                        reason="rejoined a sentence split across an interposed figure or table",
                        score=0.5,
                    )
                )
            continue
        merged.append(block)
    return merged


def _merge_title_spillovers(blocks: list[Block], ctx: Context) -> list[Block]:
    merged: list[Block] = []
    for block in blocks:
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and previous.type is BlockType.heading
            and block.type is BlockType.paragraph
            and is_title_spillover(block.text)
        ):
            previous.text = f"{previous.text} {block.text}".strip()
            ctx.warnings.add(
                LowConfidence(
                    block_id=previous.id,
                    reason=f"merged wrapped-title fragment into heading: {block.text!r}",
                    score=0.6,
                )
            )
            continue
        merged.append(block)
    return merged


def _attach_sections(blocks: list[Block]) -> None:
    current: str | None = None
    for block in blocks:
        if block.type is BlockType.heading:
            current = block.section
        elif block.section is None:
            block.section = current


def _tag_references_region(blocks: list[Block]) -> None:
    # A references region runs from a "References"/"Bibliography" heading (or the first
    # reference entry) until the next heading. Resetting at each heading is what makes
    # per-chapter bibliographies work: tagging would otherwise run away and swallow every
    # following chapter as backmatter once the first chapter's bibliography appears.
    in_references = False
    for block in blocks:
        is_backmatter_title = block.text.strip().lower() in _BACKMATTER_HEADINGS
        if block.type is BlockType.heading and not is_backmatter_title:
            in_references = False  # a different section heading ends the references region
            continue
        if is_backmatter_title or block.type is BlockType.reference_list:
            in_references = True
        if in_references:
            block.type = BlockType.backmatter


def _emit_empty_section_warnings(blocks: list[Block], ctx: Context) -> None:
    for index, block in enumerate(blocks):
        # Chapter titles (section is None) legitimately have no body; only flag sections.
        if block.type is not BlockType.heading or block.section is None:
            continue
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        if following is None or following.type is BlockType.heading:
            ctx.warnings.add(
                LowConfidence(
                    block_id=block.id,
                    reason=f"section heading has no body text: {block.text!r}",
                    score=0.5,
                )
            )


class BuildIrStage:
    name = "build_ir"

    def run(self, doc: Document, ctx: Context) -> Document:
        for block in doc.blocks:
            # fix_mojibake repairs OCR detached-diacritic artifacts ("Scholander ¨"); then
            # clean_markup turns any Marker LaTeX/HTML markup into plain tokens. Both are
            # no-ops on clean (poppler) prose, so this stays parser-agnostic.
            cleaned = rejoin_split_tokens(
                dehyphenate(normalize_ligatures(clean_markup(fix_mojibake(block.text))))
            )
            # Collapse Marker's pathological caption loops (Gate A warning, never silent).
            cleaned, removed = collapse_repetition(cleaned)
            if removed:
                ctx.warnings.add(
                    LowConfidence(
                        block_id=block.id,
                        reason=f"collapsed {removed} words of repeated OCR garble",
                        score=0.4,
                    )
                )
            block.text = cleaned

        running = detect_running_artifacts(doc.blocks)
        kept = [block for block in doc.blocks if not _is_artifact(block, running)]
        stripped = len(doc.blocks) - len(kept)
        if stripped:
            ctx.log.info("stripped_artifacts", count=stripped)

        # Refine types BEFORE the merges. Marker drops the (repeated) "Bibliography" heading as
        # a running artifact, so a reference list ("- [1] Author...") can end up adjacent to a
        # preceding unterminated paragraph (a Data Availability note ending in a URL). Typing it
        # reference_list first stops the cross-page merge (paragraph->paragraph only) from
        # absorbing the whole bibliography into that paragraph and speaking it aloud.
        for block in kept:
            if block.type is BlockType.paragraph:
                refined = classify_block(block.text)
                if refined is not BlockType.paragraph:
                    block.type = refined

        # Title spillovers first, so a wrapped-title fragment is pulled up into its
        # heading before the cross-page merge could swallow it into the next paragraph.
        kept = _merge_title_spillovers(kept, ctx)
        kept = _merge_cross_page_continuations(kept, ctx)

        _attach_sections(kept)
        _tag_references_region(kept)
        _emit_empty_section_warnings(kept, ctx)

        doc.blocks = kept
        return doc
