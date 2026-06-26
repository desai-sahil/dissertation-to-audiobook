"""The text normalizer: turn clean text into speakable text. Pure, no I/O.

`normalize_all` composes the category passes in a fixed order, then a final sweep
guarantees the no-leak invariant: the output contains none of the forbidden raw
tokens. Structured passes produce quality; the sweep guarantees correctness for any
input. The function is idempotent: normalize_all(normalize_all(x)) == normalize_all(x).
"""

from __future__ import annotations

import re

from thesis_audiobook.lexicon import Lexicon, apply_lexicon
from thesis_audiobook.normalization import greek, numbers, stats, units
from thesis_audiobook.normalization.segmentation import segment

__all__ = ["FORBIDDEN_RAW_TOKENS", "normalize_all", "segment"]

# Raw notation a voice would mangle. None may survive normalization. The unicode
# minus sign (U+2212) is included because the thesis PDF uses it for negatives.
FORBIDDEN_RAW_TOKENS: frozenset[str] = frozenset("%±^_<>[]") | {"µ", "μ", "−"}

_URL = re.compile(r"https?://\S+|www\.\S+")
_URL_SPOKEN = " the link in the text "

# Exotic dashes the PDF uses (minus sign, en/em dash, figure/hyphen variants) map to
# ASCII "-" up front so the range and negative rules apply uniformly.
_DASHES = "−‒–—―‐‑"

_SWEEP: dict[str, str] = {
    "%": " percent ",
    "±": " plus or minus ",
    "^": " to the power ",
    "_": " ",
    "<": " less than ",
    ">": " greater than ",
    "[": " ",
    "]": " ",
    "µ": " mu ",
    "μ": " mu ",
    "−": " minus ",
}


def _normalize_dashes(text: str) -> str:
    for dash in _DASHES:
        text = text.replace(dash, "-")
    return text


def _sweep_forbidden(text: str) -> str:
    for token, replacement in _SWEEP.items():
        text = text.replace(token, replacement)
    return text


def _tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def _normalize_once(text: str, lexicon: Lexicon) -> str:
    text = units.normalize_units(text)
    text = apply_lexicon(text, lexicon)
    text = greek.expand_greek_letters(text)
    text = stats.normalize_stats(text)
    text = numbers.normalize_numbers(text)
    return text


def normalize_all(text: str, lexicon: Lexicon) -> str:
    text = _URL.sub(_URL_SPOKEN, text)
    text = _normalize_dashes(text)
    # Run the token passes to a fixed point: separating a digit from letters can
    # expose a unit or grapheme (56mM -> mM, gs4 -> gs) that an earlier pass missed.
    # The transforms only ever replace notation with words, so this converges fast.
    for _ in range(6):
        updated = _normalize_once(text, lexicon)
        if updated == text:
            break
        text = updated
    text = _sweep_forbidden(text)
    return _tidy(text)
