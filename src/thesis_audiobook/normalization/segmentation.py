"""Sentence segmentation that knows scientific abbreviations. Pure, no I/O.

`segment` PARTITIONS the input: concatenating the returned segments reproduces the
text exactly (every character in exactly one segment). It does not break after known
abbreviations (et al., e.g., i.e., Fig., vs., approx., cf.) or inside a URL, so TTS
does not get spurious sentence pauses. The partition guarantee is what the chunk
planner relies on for its conservation invariant.
"""

from __future__ import annotations

import re

_ABBREVIATIONS = (
    "et al.", "e.g.", "i.e.", "fig.", "vs.", "approx.", "cf.", "eq.",
    "sec.", "no.", "dr.", "st.", "al.", "spp.", "ca.",
)  # fmt: skip

_URL = re.compile(r"https?://\S+|www\.\S+")
_SENTENCE_END = re.compile(r"[.!?]+")


def _protected_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    lowered = text.lower()
    for abbreviation in _ABBREVIATIONS:
        start = lowered.find(abbreviation)
        while start != -1:
            spans.append((start, start + len(abbreviation)))
            start = lowered.find(abbreviation, start + 1)
    for match in _URL.finditer(text):
        spans.append(match.span())
    return spans


def _covered(index: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in spans)


def segment(text: str) -> list[str]:
    if not text:
        return []
    spans = _protected_spans(text)
    segments: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        if _covered(match.start(), spans):
            continue
        end = match.end()
        while end < len(text) and text[end].isspace():
            end += 1
        segments.append(text[start:end])
        start = end
    if start < len(text):
        segments.append(text[start:])
    return segments
