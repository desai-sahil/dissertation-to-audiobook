"""Acronym expansion. Pure, deterministic, no I/O.

The lexicon decides expand-as-words (ABA -> "abscisic acid") versus spell-as-letters
(MCMC -> "M C M C"). Longest grapheme first so compound acronyms win.
"""

from __future__ import annotations

from thesis_audiobook.lexicon import Lexicon, apply_entries


def expand_acronyms(text: str, lexicon: Lexicon) -> str:
    entries = sorted(
        lexicon.by_category("acronym"), key=lambda entry: len(entry.grapheme), reverse=True
    )
    return apply_entries(text, entries)
