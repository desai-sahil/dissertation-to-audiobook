"""Pure IR-cleanup helpers for the build_ir stage. No I/O.

These operate on already-extracted text and on a Document, repairing PDF-extraction
artifacts (de-hyphenation, ligatures), classifying blocks, and detecting structure.
Everything here is deterministic and unit-testable offline; the actual parsing I/O
lives in the parser adapters.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import Block, BlockType

_LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st",
    " ": " ", "​": "", "﻿": "",
}  # fmt: skip

_CHAPTER = re.compile(r"^\s*CHAPTER\s+(\d+)\s*$", re.IGNORECASE)
_SECTION = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.*\S)\s*$")
_SECTION_NUMBER_ONLY = re.compile(r"^\s*(\d+(?:\.\d+)+)\s*$")
# A reference entry: "[1] Author..." or Marker's markdown list form "- [1] Author...".
_REFERENCE = re.compile(r"^\s*[-*•]?\s*\[(\d+)\]\s")
_PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")


def normalize_ligatures(text: str) -> str:
    for ligature, replacement in _LIGATURES.items():
        text = text.replace(ligature, replacement)
    return text


def dehyphenate(text: str) -> str:
    """Rejoin words split across a line break, then flatten remaining line breaks."""
    text = re.sub(r"(\w)[-­]\n(\w)", r"\1\2", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    # Rejoin en/em-dash compounds the reflow split across a wrap (PYR– PP2C -> PYR–PP2C).
    text = re.sub(r"(\w[–—])\s+(\w)", r"\1\2", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def ends_hyphenated(text: str) -> bool:
    """A block ending in a lowercase-letter hyphen is a word split across a page break."""
    return bool(re.search(r"[a-z][-­]$", text.strip()))


# Domain tokens the PDF extractor space-splits, rejoined conservatively (word-bounded).
_REJOIN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bg\s+s\b"), "gs"),
    (re.compile(r"\bg\s+oxz\b"), "goxz"),
    (re.compile(r"\bH2\s+O2\b"), "H2O2"),
    (re.compile(r"\bH2\s+O\b"), "H2O"),
    (re.compile(r"\bC\s+O2\b"), "CO2"),
    (re.compile(r"\bV\s+PD\b"), "VPD"),
    (re.compile(r"ψ\s+xyl"), "ψ_xyl"),
    (re.compile(r"ψ\s+ssc"), "ψ_ssc"),
]

_SPILLOVER_START = re.compile(r"(and|with|or|of|the|for|to|in|via)\b", re.IGNORECASE)


def rejoin_split_tokens(text: str) -> str:
    for pattern, replacement in _REJOIN:
        text = pattern.sub(replacement, text)
    return text


def is_title_spillover(text: str) -> bool:
    """A short, connective, unterminated fragment that is a wrapped heading line."""
    stripped = text.strip()
    return (
        0 < len(stripped) <= 60
        and bool(_SPILLOVER_START.match(stripped))
        and not stripped.endswith((".", "!", "?", ":"))
    )


def looks_like_page_number(text: str) -> bool:
    return bool(_PAGE_NUMBER.match(text))


def is_reference_entry(text: str) -> bool:
    return bool(_REFERENCE.match(text))


def classify_block(text: str) -> BlockType:
    """Best-effort block-type classification from text content."""
    stripped = text.strip()
    if not stripped:
        return BlockType.paragraph
    if is_reference_entry(stripped):
        return BlockType.reference_list
    if _CHAPTER.match(stripped) or _SECTION.match(stripped):
        return BlockType.heading
    return BlockType.paragraph


def detect_running_artifacts(blocks: list[Block], *, min_repeats: int = 3) -> set[str]:
    """Find short lines repeated across pages (running headers/footers)."""
    counts: dict[str, int] = {}
    for block in blocks:
        key = block.text.strip()
        if 0 < len(key) <= 60:
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count >= min_repeats}
