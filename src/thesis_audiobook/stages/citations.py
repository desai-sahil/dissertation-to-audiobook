"""Stage: citation verbalizer. The resolution helpers are pure and unit-tested.

Numeric markers ([1], [1, 2, 3], [15]) resolve against the parsed bibliography to a
spoken author-year form per the profile's citation policy:
  drop  -> remove the marker entirely
  brief -> first author plus "and colleagues" (if multiple) and the year
  full  -> all authors and the year
"et al." in prose becomes "and colleagues". Years stay as digits here and are spelled
by the normalizer downstream.

When a marker immediately follows an in-text author mention ("Bacheva et al.[21]",
"Medlyn [14]"), the citation voices the year only, so the name is not read twice.
"""

from __future__ import annotations

import re

from thesis_audiobook.context import Context
from thesis_audiobook.ir import BibEntry, Citation, Document, Handling
from thesis_audiobook.normalization.numbers import year_to_words

_MARKER = re.compile(r"\s?\[([\d,\s]+)\]")
_ET_AL = re.compile(r"\bet al\.", re.IGNORECASE)


def expand_et_al(text: str) -> str:
    return _ET_AL.sub("and colleagues", text)


def _surname(author: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", author)
    return words[-1] if words else ""


def _author_named_inline(preceding: str, surname: str) -> bool:
    """True if `surname` is the last name in the prose just before the marker (optionally
    trailed by 'et al.'), so 'Bacheva et al.[21]' / 'Medlyn [14]' read as year only. A
    hyphenated compound is allowed, so 'Ball-Berry [n]' citing 'Ball et al.' is caught."""
    if not surname:
        return False
    # Citations run before dash normalization, so fold en/em/figure dashes to ASCII
    # first; the source writes compounds like "Ball-Berry" with an en-dash (U+2013).
    tail = re.sub(r"[‐-―−]", "-", preceding[-60:])
    # Match the surname CASE-SENSITIVELY: a real author mention is a capitalized proper
    # noun, so a common lowercase word ("cell wall [12]" for an author named Wall) is not
    # mistaken for an inline author. The trailing "et al." stays case-insensitive.
    pattern = rf"\b{re.escape(surname)}(?:-[A-Za-z]+)*\b\W*(?:(?i:et al\.?))?\s*$"
    return bool(re.search(pattern, tail))


def spoken_citation(entry: BibEntry, policy: str, *, suppress_name: bool = False) -> str:
    # Year is spelled here (twenty nineteen) so the normalizer leaves it alone, and no
    # comma precedes it: "Smith and colleagues twenty nineteen".
    year = year_to_words(entry.year) if entry.year is not None else ""
    authors = entry.authors
    if suppress_name:
        return year
    if policy == "full" and authors:
        names = ", ".join(authors)
        return f"{names} {year}".strip()
    if authors:
        lead = authors[0]
        if len(authors) > 1:
            lead = f"{lead} and colleagues"
        return f"{lead} {year}".strip()
    return year


def resolve_citations(
    text: str,
    citations: dict[str, Citation],
    bibliography: dict[str, BibEntry],
    policy: str,
) -> str:
    if policy == "drop":
        text = _MARKER.sub("", text)
        return expand_et_al(text)

    def replace(match: re.Match[str]) -> str:
        preceding = match.string[: match.start()]
        numbers = [token.strip() for token in match.group(1).split(",") if token.strip()]
        spokens: list[str] = []
        for index, number in enumerate(numbers):
            citation = citations.get(number)
            if citation is None or citation.bib_key is None:
                continue
            entry = bibliography.get(citation.bib_key)
            if entry is None:
                continue
            # Only the first marker in a group can sit right after the inline name.
            suppress = (
                index == 0
                and entry.authors
                and _author_named_inline(preceding, _surname(entry.authors[0]))
            )
            spokens.append(spoken_citation(entry, policy, suppress_name=bool(suppress)))
        if not spokens:
            return ""
        return " " + "; ".join(spokens)

    return expand_et_al(_MARKER.sub(replace, text))


class CitationsStage:
    name = "citations"

    def run(self, doc: Document, ctx: Context) -> Document:
        policy = ctx.config.profile.citation_policy
        for block in doc.blocks:
            if block.keep and block.handling is Handling.speak:
                block.spoken = resolve_citations(
                    block.current_text(), doc.citations, doc.bibliography, policy
                )
        return doc
