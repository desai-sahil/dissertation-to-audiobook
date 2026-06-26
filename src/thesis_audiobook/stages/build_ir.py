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

The GROBID citation map is merged in the ingest stage (which holds both port
outputs). Running build_ir on already-clean IR (the mock fixture) is a no-op.
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


def _merge_cross_page_continuations(blocks: list[Block], ctx: Context) -> list[Block]:
    merged: list[Block] = []
    for block in blocks:
        previous = merged[-1] if merged else None
        if not (
            previous is not None
            and previous.type is BlockType.paragraph
            and block.type is BlockType.paragraph
        ):
            merged.append(block)
            continue
        if ends_hyphenated(previous.text):
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
            # Benign reading-order repair (whitespace only, no content altered).
            previous.text = f"{previous.text.rstrip()} {block.text.lstrip()}"
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
    in_references = False
    for block in blocks:
        if not in_references:
            is_marker = block.type is BlockType.reference_list
            is_heading = block.text.strip().lower() in _BACKMATTER_HEADINGS
            in_references = is_marker or is_heading
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
            # clean_markup first turns any Marker LaTeX/HTML markup into plain tokens; it is
            # a no-op on clean (poppler) prose, so this stays parser-agnostic.
            block.text = rejoin_split_tokens(
                dehyphenate(normalize_ligatures(clean_markup(block.text)))
            )

        running = detect_running_artifacts(doc.blocks)
        kept = [block for block in doc.blocks if not _is_artifact(block, running)]
        stripped = len(doc.blocks) - len(kept)
        if stripped:
            ctx.log.info("stripped_artifacts", count=stripped)

        # Title spillovers first, so a wrapped-title fragment is pulled up into its
        # heading before the cross-page merge could swallow it into the next paragraph.
        kept = _merge_title_spillovers(kept, ctx)
        kept = _merge_cross_page_continuations(kept, ctx)

        for block in kept:
            if block.type is BlockType.paragraph:
                refined = classify_block(block.text)
                if refined is not BlockType.paragraph:
                    block.type = refined

        _attach_sections(kept)
        _tag_references_region(kept)
        _emit_empty_section_warnings(kept, ctx)

        doc.blocks = kept
        return doc
