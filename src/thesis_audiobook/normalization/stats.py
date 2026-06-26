"""Statistical and arithmetic operators. Pure, deterministic, no I/O.

Runs after lexicon expansion and before numeral spelling, so "p<0.05" becomes
"p less than 0.05" and then "p less than zero point zero five". URLs are protected by
the orchestrator before this runs, so the slash rule does not mangle links.
"""

from __future__ import annotations

# Multi-character and unicode operators first so they win over single characters.
_OPERATORS: list[tuple[str, str]] = [
    ("≤", " less than or equal to "),
    ("≥", " greater than or equal to "),
    ("≈", " approximately "),
    ("±", ", plus or minus, "),
    ("×", " times "),
    ("·", " times "),
    ("*", " asterisk "),
    ("<", " less than "),
    (">", " greater than "),
    ("=", " equals "),
    ("/", " over "),
]


def normalize_stats(text: str) -> str:
    for raw, spoken in _OPERATORS:
        text = text.replace(raw, spoken)
    return text
