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

# Full URLs (incl. protocol-less www) plus bare "domain.tld/path" with a KNOWN TLD - so a
# protocol-less or PDF-split link is caught before the slash rule voices "/" as "over",
# without swallowing filenames like results.csv/sheet1 (.csv is not a TLD). Matched greedily,
# then any trailing sentence punctuation or closing bracket is handed back, so a link never
# eats the period that ends its sentence or the parenthesis that encloses it.
_TLD = r"com|org|net|io|edu|gov|ai|co|dev|app|info|me|xyz"
_URL = re.compile(rf"(?:https?://|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:{_TLD})/\S+")
_URL_SPOKEN = " the link in the text "
_URL_TRAILING = ").,;:]'\""
# A PDF-split URL becomes adjacent link phrases (sometimes with stray punctuation between);
# collapse the run to one.
_DUP_LINK = re.compile(r"(?:the link in the text[\s.,;]*){2,}")


def _replace_urls(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        url = match.group(0)
        trailing = ""
        while url and url[-1] in _URL_TRAILING:
            trailing = url[-1] + trailing
            url = url[:-1]
        return _URL_SPOKEN + trailing

    return _URL.sub(repl, text)


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


# A phrase immediately followed by its own gloss in parentheses, e.g.
# "abscisic acid (abscisic acid)" (left when an acronym is expanded back to the term it
# was defining) or "outside-xylem (outside xylem)" (hyphen vs space). Captured groups
# stay within a clause: no sentence punctuation inside either side.
_REDUNDANT_PAREN = re.compile(r"([A-Za-z][\w-]*(?:[ \t][\w-]+)*)[ \t]*\(([A-Za-z][\w \t-]*?)\)")


def _paren_key(text: str) -> str:
    return re.sub(r"[\s_-]+", " ", text).strip().lower()


def _collapse_redundant_parenthetical(text: str) -> str:
    """Drop a parenthetical gloss that just repeats the multi-word phrase before it.

    "abscisic acid (abscisic acid)" -> "abscisic acid"; "outside-xylem (outside xylem)" ->
    "outside-xylem". A single repeated word ("conductance (conductance)") and a real gloss
    ("(A B A)") are kept. Looped to a fixed point so chained repeats fully collapse and the
    pass is idempotent.
    """

    def repl(match: re.Match[str]) -> str:
        before, inside = match.group(1), match.group(2)
        inside_key = _paren_key(inside)
        # Only collapse a multi-word full-phrase restatement, not a lone repeated noun.
        if " " in inside_key and _paren_key(before).endswith(inside_key):
            return before
        return match.group(0)

    for _ in range(4):
        collapsed = _REDUNDANT_PAREN.sub(repl, text)
        if collapsed == text:
            break
        text = collapsed
    return text


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
    text = _replace_urls(text)
    text = _DUP_LINK.sub("the link in the text ", text)
    text = _normalize_dashes(text)
    # Run the token passes to a fixed point: separating a digit from letters can
    # expose a unit or grapheme (56mM -> mM, gs4 -> gs) that an earlier pass missed.
    # The transforms only ever replace notation with words, so this converges fast.
    for _ in range(6):
        updated = _normalize_once(text, lexicon)
        if updated == text:
            break
        text = updated
    # Collapse after the sweep, so a forbidden token between the phrase and its gloss
    # (e.g. an underscore) is already folded and cannot defeat the duplicate check.
    text = _sweep_forbidden(text)
    text = _collapse_redundant_parenthetical(text)
    return _tidy(text)
