"""Citation naturalizer: treat in-text references as MACHINERY to discard. Pure, no I/O.

NotebookLM-style: a narration does not read "Smith et al., 2020" or reference numbers aloud. So
this (1) DETERMINISTICALLY strips the pure reference markers - bracketed [12], bare fused
"word.41", parenthetical "(Geiger et al., 2009)", and a number trailing "et al." - and (2) where
the author IS the grammar of the sentence ("Chalmer et al. note that ..."), GENERICIZES the
attribution to a vague phrase ("researchers note that ..."). The genericizing is the ONE place we
let the model rewrite prose, and it is bounded by construction: the model only maps each author
mention to one phrase from a FIXED set, and the deterministic layer substitutes just that span -
the claim/finding is never touched. Offline (mock LLM) the genericizing is skipped and the mention
degrades to natural "Author and others", so offline output stays deterministic.

Superscript "<sup>N</sup>" citations are dropped later by the latex normalizer (where the sup
logic already lives); this module handles every other in-text form. No bibliography is consulted.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast

NATURALIZE_VERSION = "cite-generic-v2"

# --- deterministic marker stripping ----------------------------------------------------------
# A bracketed numeric citation: " [12]", "[1, 2, 3]".
_BRACKET = re.compile(r"\s?\[\s*\d[\d,\s]*\]")
# A reference number trailing "et al." ("et al.,50", "et al. 31", "et al.31"); keep "et al.".
_ETAL_NUM = re.compile(r"(\bet al\.?)[,\s]*\d+(?:\s*,\s*\d+)*", re.IGNORECASE)
# A reference number fused onto a word by a period OR a comma with NO following space:
# "dynamics.41", "state.18, 19", "diseases.10-16", "group,20, 21". Captured as (word)(sep+numbers).
# A decimal ("0.4") has a digit before the period so it never matches; single-capital initials
# ("M.26") have <2 letters; abbreviations ("No.1", "Fig.3") are in _ABBR; a code ("No.9657K286")
# has an alnum after the run. Real prose "word, 20" (a SPACE after the comma) is NOT matched - the
# regex requires the digit immediately after the separator, the fused-citation signature.
_BARE = re.compile(r"\b([A-Za-z][A-Za-z]+)([.,]\d+(?:\s*[,–—-]\s*\d+)*)(?![A-Za-z0-9])")
_ABBR = frozenset(
    {"etc", "approx", "fig", "figs", "eqn", "sec", "vol", "ref", "tab", "chap", "app", "rev",
     "ver", "ave", "max", "min", "seq", "eds"}
)  # fmt: skip
# A parenthetical CITATION: it contains "et al." OR an explicit "Author, YEAR" pair. A bare year, a
# date, a time, or a measured value in parentheses ("(Summer 2020)", "(2019)", "(n = 2020)", "(20
# July 2018, 1500-1700 hrs)") is NOT a citation and is kept - the review found the old year-only
# detector silently deleted real data.
_PAREN = re.compile(
    r"\s?\((?:[^()]*?(?:et al\.?|[A-Z][A-Za-z.'\-]+,\s*(?:19|20)\d\d[a-z]?)[^()]*?)\)"
)
_ET_AL = re.compile(r"\bet al\.?", re.IGNORECASE)


# Two+ numbers separated by a COMMA: the only fused-list form treated as a citation after a
# CAPITALIZED word. A dash/en-dash RANGE ("Cat.13-45", "Lot.118-22", "Bud.118-490") is almost
# always a code/catalog/cross, not a citation list, so it is NOT matched here (review-found: the
# old comma-or-dash rule silently deleted real lot/catalog/cross identifiers).
_NUM_COMMA_LIST = re.compile(r"\d\s*,\s*\d")


def _is_capital_citation(word: str, nums: str) -> bool:
    """A capitalized fused word + numbers reads as a citation only for a 3+ letter non-abbreviation
    word whose numbers are a COMMA list. Single numbers and dash ranges stay (code/cultivar)."""
    return (
        len(word) >= 3
        and not word.islower()
        and word.lower() not in _ABBR
        and bool(_NUM_COMMA_LIST.search(nums))
    )


def _strip_bare(match: re.Match[str]) -> str:
    """Drop a fused reference number after a real content word of 3+ letters, unless it is a known
    abbreviation. PERIOD-fused ("dynamics.41" -> "dynamics."): a LOWERCASE word always strips; a
    CAPITALIZED word strips only as a COMMA list ("Stroock Group.20, 21" -> "Stroock Group."), since
    a capital + single number or dash range is ambiguous with a real code ("Bud.118", "Cat.13-45"),
    left intact. COMMA-fused with no space ("group,20, 21" -> "group"): strips only as a LIST of 2+
    numbers (a lone "Table,2" is a fused cross-ref, kept), and drops the comma (it was the
    citation's, not the prose's). Capital strips are surfaced as warnings by the citations stage
    (convention 9). Initials ("M.26"), abbreviations ("No.1"), decimals ("0.4"), and codes
    ("No.9657K286") never match by construction."""
    word, nums = match.group(1), match.group(2)
    if len(word) < 3 or word.lower() in _ABBR:
        return match.group(0)
    if nums[0] == ",":  # comma-fused: a 2+ number list is a citation; drop the comma + the list
        return word if _NUM_COMMA_LIST.search(nums) else match.group(0)
    if word.islower() or _is_capital_citation(word, nums):  # period-fused
        return f"{word}."  # the word + its sentence period, citation number(s) removed
    return match.group(0)


def capitalized_citation_strips(text: str) -> list[str]:
    """The CAPITALIZED fused spans strip_markers will actually remove, returned verbatim so the
    citations stage can warn (a capital citation list is usually right but could be a code/cross-ref
    series like "Bud.9, 62, 118" or "Table,2, 3" - convention 9: surface, never silently delete).
    Lowercase strips (clearly citations) are not warned."""
    return [
        m.group(0)
        for m in _BARE.finditer(text)
        if not m.group(1).islower() and _strip_bare(m) != m.group(0)
    ]


def strip_markers(text: str) -> str:
    """Remove the pure (non-narrative) reference markers, keeping the surrounding prose intact."""
    text = _ETAL_NUM.sub(r"\1", text)  # "et al.,50" -> "et al."
    text = _BRACKET.sub("", text)  # "[12]" -> ""
    text = _PAREN.sub("", text)  # "(Geiger et al., 2009)" -> ""
    text = _BARE.sub(_strip_bare, text)  # "dynamics.41" -> "dynamics."; "M.26"/"Fig.3" kept
    # drop a now-orphaned citation lead-in, then tidy spaces left before sentence punctuation
    text = _DANGLING.sub(r"\1", text)
    text = re.sub(r"\s+([.,;:)])", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def expand_et_al(text: str) -> str:
    """Leftover "et al." -> "and others" (how a reader says it), the offline fallback for a
    narrative mention that was not genericized."""
    return _ET_AL.sub("and others", text)


# --- narrative genericizing (LLM picks a phrase from a fixed set) -----------------------------
# A narrative author mention: a capitalized surname (optionally "X and Y") followed by "et al."
# The author is part of the sentence grammar, so it cannot just be deleted. Anchored on "et al."
# only (the source's form); a bare "X and others" is too easily a common noun phrase to genericize.
_NARRATIVE = re.compile(r"\b[A-Z][A-Za-z'’.\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z'’.\-]+)*\s+et al\.?")
# The only phrases the model may choose - a generic attribution can carry no claim of its own. All
# PLURAL, to agree with the plural verb that followed "X et al." ("...et al. show" -> "...show").
GENERIC_PHRASES = frozenset(
    {"researchers", "other researchers", "the authors", "several studies", "prior studies",
     "earlier studies"}
)  # fmt: skip
# A citation that was the grammatical object of a lead-in leaves it dangling once removed
# ("as shown in [12]." -> "as shown in ."); drop the orphaned lead-in when it now abuts sentence
# punctuation. Only fires on an unambiguous lead-in immediately before punctuation, so normal prose
# ("according to the data") is never touched.
_DANGLING = re.compile(
    r"\b(?:(?:as )?(?:shown|seen|reviewed|reported|described|demonstrated|illustrated)\s+"
    r"(?:in|by)|according to|referred to)\s*([.,;:)])",
    re.IGNORECASE,
)


def find_narrative_mentions(text: str) -> list[str]:
    """The distinct "Author et al." spans in reading order (deduped)."""
    seen: dict[str, None] = {}
    for match in _NARRATIVE.finditer(text):
        seen.setdefault(match.group(0), None)
    return list(seen)


def build_genericize_prompt(mentions: list[str]) -> str:
    options = ", ".join(sorted(GENERIC_PHRASES))
    payload = json.dumps(mentions, ensure_ascii=False)
    return (
        "An audiobook narration should not name citation authors aloud. For each author mention "
        "below, choose the GENERIC attribution phrase that best replaces it so the sentence still "
        "reads naturally (vary your choices; match plurality - most take a plural verb). You write "
        "no other text.\n"
        f"Allowed phrases ONLY: {options}.\n"
        "Return ONLY JSON mapping each mention to one allowed phrase, e.g. "
        '{"Chalmer et al.": "researchers"}.\n\n'
        f"Mentions:\n{payload}"
    )


def parse_genericization(raw: str) -> dict[str, str]:
    """Parse {mention: phrase}; keep only entries whose phrase is in the allowed set (so the model
    cannot inject free text). Empty on any failure (offline mock -> no genericizing)."""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        loaded = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    out: dict[str, str] = {}
    for mention, phrase in cast("dict[str, Any]", loaded).items():
        if isinstance(phrase, str) and phrase.strip().lower() in GENERIC_PHRASES:
            out[str(mention)] = phrase.strip().lower()
    return out


def apply_genericization(text: str, mapping: dict[str, str]) -> str:
    """Replace each mapped narrative mention with its generic phrase (longest first, whole-span)."""
    for mention in sorted(mapping, key=len, reverse=True):
        text = re.sub(
            r"(?<![A-Za-z0-9])" + re.escape(mention) + r"(?![A-Za-z0-9])", mapping[mention], text
        )
    return text


# A genericized citation LIST reads as run-together generics ("prior studies several studies and
# Zhu") because each "X et al." was mapped separately. Collapse a run of 2+ generic phrases (plus an
# optional trailing "and <Author>") into a single "several studies". Requires >=2 generics, so a
# lone generic followed by a sentence subject ("researchers, Stomata regulate") is never touched.
_GENERIC_ALT = "|".join(sorted((re.escape(p) for p in GENERIC_PHRASES), key=len, reverse=True))
_COLLAPSE = re.compile(
    rf"\b(?:{_GENERIC_ALT})(?:[\s,]+(?:and\s+)?(?:{_GENERIC_ALT}))+"
    r"(?:[\s,]+and\s+[A-Z][A-Za-z'’.\-]+)?"
)


def collapse_citation_run(text: str) -> str:
    """Fold a run of >=2 genericized citations (a list) into one phrase: "prior studies several
    studies and Zhu" -> "several studies"."""
    return _COLLAPSE.sub("several studies", text)


def naturalize_citations(text: str, mapping: dict[str, str] | None = None) -> str:
    """Full deterministic pass for one block: strip markers, genericize known mentions, and read
    any remaining "et al." as "and others"."""
    text = strip_markers(text)
    if mapping:
        text = collapse_citation_run(apply_genericization(text, mapping))
    return expand_et_al(text)
