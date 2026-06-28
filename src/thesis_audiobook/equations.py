"""Pure helpers for display-equation announcement, shared by the v1 math stage and the v2 engine.

Equations are announced by their printed number, never read symbol by symbol (the announce-only
decision: a spoken gloss hallucinated). An unnumbered display equation is an intermediate step with
no number to announce, so it is dropped from the audio. No I/O.
"""

from __future__ import annotations

import re

from thesis_audiobook.normalization.numbers import section_to_words

# A real equation number: \tag{2.4}, or a bare "(2.4)" that upstream folded into the LaTeX.
_TAG = re.compile(r"\\tag\{\s*\(?\s*([0-9]+(?:\.[0-9]+)*)\s*\)?\s*\}")
_TRAILING_NUMBER = re.compile(r"\(\s*([0-9]+(?:\.[0-9]+)+)\s*\)\s*$")


def equation_number(latex: str) -> str | None:
    """Extract the thesis's own equation number from a display equation's LaTeX, or None."""
    match = _TAG.search(latex) or _TRAILING_NUMBER.search(latex.strip())
    return match.group(1) if match else None


def equation_announcement(latex: str) -> str | None:
    """Spoken announcement for a display equation ("Equation two point four."), or None if it has no
    printed number (an intermediate step -> dropped from the audio)."""
    number = equation_number(latex)
    return f"Equation {section_to_words(number)}." if number is not None else None
