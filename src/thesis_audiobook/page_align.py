"""Assign each IR block its physical page by matching block text to the PDF's per-page text. Pure.

The v2 vision escalation needs a block -> page-image map, but Marker only emits page anchors in some
of its output (Zhu has them, Gao/Jain do not - it depends on the Marker version/settings). This
derives the page independently: poppler's pdftotext gives the text of each physical page (the same
poppler that renders the page images), and each block is placed on the first page that shares enough
of its distinctive words.

Matching is by WORD OVERLAP, not substring: Marker (de-hyphenated, reflowed) and poppler (raw) emit
different character sequences for the same paragraph, so a contiguous signature rarely matches, but
the distinctive words still overlap. A block that matches no page (heavily mangled notation) is left
without a page - escalation just skips it, never mis-locates it. Page text comes from the edge
(adapters/pdf_render.extract_pages_text); this module is pure.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import Block

_ALNUM = re.compile(r"[a-z0-9]+")
_MIN_WORD_LEN = 4  # only "distinctive" words count (skip the/of/and and 1-3 char noise)
_OPENING_WORDS = 25  # match on the block's opening, where extractors agree best
_MIN_WORDS = 4  # fewer distinctive words than this is too ambiguous to place
_OVERLAP_THRESHOLD = 0.5  # >= this fraction of the block's words on a page -> it is that page


def _distinctive_words(text: str, limit: int | None = None) -> list[str]:
    words = [w for w in _ALNUM.findall(text.lower()) if len(w) >= _MIN_WORD_LEN]
    return words[:limit] if limit is not None else words


def assign_pages_by_text(blocks: list[Block], page_texts: list[str]) -> int:
    """Set block.page (1-indexed) for each unpaged block to the first page whose text shares at
    least _OVERLAP_THRESHOLD of the block's distinctive opening words. Returns how many were
    assigned; an unmatched block is left as None.

    Matched globally (every page), not with a forward cursor: blocks and pages are mostly in order,
    but Marker emits figures/captions/equations out of physical order, and a cursor lets one of them
    jump ahead and strand the real body paragraphs behind it. Distinctive-word overlap on the
    opening is specific enough that the first qualifying page is the right one."""
    page_word_sets = [set(_distinctive_words(text)) for text in page_texts]
    assigned = 0
    for block in blocks:
        if block.page is not None:
            continue
        opening = set(_distinctive_words(block.text, _OPENING_WORDS))
        if len(opening) < _MIN_WORDS:
            continue
        for index, page_words in enumerate(page_word_sets):
            hits = sum(1 for word in opening if word in page_words)
            if hits / len(opening) >= _OVERLAP_THRESHOLD:
                block.page = index + 1
                assigned += 1
                break
    return assigned
