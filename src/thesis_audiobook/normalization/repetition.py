"""Collapse pathological OCR/templating repetition. Pure, no I/O.

Marker occasionally falls into a generation loop on a hard figure caption, emitting the same
short phrase dozens or hundreds of times ("(E, and E, and E, and ..."). Two passes clean this
up, both returning a word-removed count so the caller surfaces a warning rather than editing
silently:

  1. Exact periodic collapse: any unit of up to eight words that repeats four-or-more times in
     a row (spanning at least eight words) is reduced to a single copy. This handles a cleanly
     periodic loop and a shredded equation typeset as "x x x x".
  2. Lexical-diversity truncation: a real OCR loop is rarely perfectly periodic, but it always
     has a tiny vocabulary. If a long block contains a sliding window that is almost entirely
     made of the same few words, the readable head is kept and the degenerate tail is dropped.
     English prose never trips this, so it is safe to run on every block.
"""

from __future__ import annotations

_MIN_REPEATS = 4
_MAX_UNIT = 8
_MIN_SPAN = 8

# Diversity guard: in a window this wide, prose always has more than this many distinct words.
_WINDOW = 10
_MIN_DISTINCT = 3
_MIN_BLOCK = 30


def _collapse_periodic(words: list[str]) -> list[str]:
    out: list[str] = []
    i, n = 0, len(words)
    while i < n:
        collapsed = False
        # Shortest unit first, so the fundamental period wins ("E, and" over "E, and E, and").
        for unit_len in range(1, min(_MAX_UNIT, (n - i) // _MIN_REPEATS) + 1):
            unit = words[i : i + unit_len]
            repeats, j = 1, i + unit_len
            while j + unit_len <= n and words[j : j + unit_len] == unit:
                repeats += 1
                j += unit_len
            if repeats >= _MIN_REPEATS and repeats * unit_len >= _MIN_SPAN:
                out.extend(unit)  # keep one copy, drop the rest
                i = j
                collapsed = True
                break
        if not collapsed:
            out.append(words[i])
            i += 1
    return out


def _truncate_low_diversity(words: list[str]) -> list[str]:
    if len(words) < _MIN_BLOCK:
        return words
    for start in range(len(words) - _WINDOW + 1):
        window = words[start : start + _WINDOW]
        if len(set(window)) <= _MIN_DISTINCT:
            # An OCR loop begins here; keep the readable head, drop the degenerate tail.
            return words[:start]
    return words


def collapse_repetition(text: str) -> tuple[str, int]:
    """Collapse repeated word-runs and truncate OCR loops. Returns (text, words_removed)."""
    words = text.split()
    n = len(words)
    if n < _MIN_SPAN:
        return text, 0
    # Truncate first, while a real OCR loop is still dense enough to trip the diversity guard;
    # then collapse any exact periodic repeats left in the salvaged head.
    cleaned = _collapse_periodic(_truncate_low_diversity(words))
    removed = n - len(cleaned)
    return (" ".join(cleaned), removed) if removed else (text, 0)
