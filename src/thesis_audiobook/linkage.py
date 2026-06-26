"""Pure citation-linkage audit over a Document. No I/O.

Reports what fraction of the inline numeric markers in the body resolve to a
bibliography entry, and which markers do not, so the parse step can surface the
unresolved ones instead of silently dropping attribution.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import BlockType, Document

_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_BODY_TYPES = {BlockType.paragraph, BlockType.heading, BlockType.figure_caption}


def body_markers(doc: Document) -> set[str]:
    markers: set[str] = set()
    for block in doc.blocks:
        if block.type in _BODY_TYPES:
            for match in _MARKER.finditer(block.text):
                for number in match.group(1).split(","):
                    markers.add(number.strip())
    return markers


def citation_linkage(doc: Document) -> tuple[float, list[str], list[str]]:
    """Return (rate, resolved markers, unresolved markers)."""
    markers = body_markers(doc)
    resolved: list[str] = []
    unresolved: list[str] = []
    for marker in markers:
        citation = doc.citations.get(marker)
        if citation is not None and citation.bib_key in doc.bibliography:
            resolved.append(marker)
        else:
            unresolved.append(marker)
    rate = len(resolved) / len(markers) if markers else 1.0
    return rate, sorted(resolved, key=int), sorted(unresolved, key=int)
