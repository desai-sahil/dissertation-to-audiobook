"""Stage: citation verbalizer. The resolution helpers are pure and unit-tested.

Numeric markers ([1], [1, 2, 3], [15]) resolve against the parsed bibliography to a
spoken author-year form per the profile's citation policy:
  drop  -> remove the marker entirely
  brief -> up to two surnames, then "and others", plus the year
  full  -> all authors and the year
"et al." in prose becomes "and others". Years stay as digits here and are spelled by the
normalizer downstream. When a marker immediately follows an in-text author mention
("Bacheva et al.[21]", "Medlyn [14]"), only the year is voiced, so the name isn't doubled.

With a real LLM, an optional naturalization pass replaces each marker with a natural
spoken phrase ("as shown by Jain in twenty twenty-one"), position-aware, claim-preserving
(only the marker token is replaced), cached, and validated; anything that drops the author
or year falls back to the deterministic rendering. Offline (mock LLM) it is a no-op.
"""

from __future__ import annotations

import hashlib
import json
import re

from thesis_audiobook.citation_naturalize import (
    NATURALIZE_VERSION,
    build_naturalize_prompt,
    parse_naturalization,
    render_citation,
)
from thesis_audiobook.context import Context
from thesis_audiobook.ir import BibEntry, Citation, Document, Handling
from thesis_audiobook.normalization.numbers import year_to_words

_MARKER = re.compile(r"\s?\[([\d,\s]+)\]")
_ET_AL = re.compile(r"\bet al\.?", re.IGNORECASE)


def expand_et_al(text: str) -> str:
    # "et al." -> "and others" (never "colleagues"): how a reader would say it aloud.
    return _ET_AL.sub("and others", text)


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


def _authors_phrase(entry: BibEntry) -> str:
    """Brief spoken author phrase: one surname, "X and Y", or "X and others" (never
    "colleagues")."""
    surnames = [_surname(author) or author for author in entry.authors]
    if not surnames:
        return ""
    if len(surnames) == 1:
        return surnames[0]
    if len(surnames) == 2:
        return f"{surnames[0]} and {surnames[1]}"
    return f"{surnames[0]} and others"


def spoken_citation(entry: BibEntry, policy: str, *, suppress_name: bool = False) -> str:
    # Year is spelled here (twenty nineteen) so the normalizer leaves it alone, and no
    # comma precedes it. Brief style names up to two surnames, then "and others".
    year = year_to_words(entry.year) if entry.year is not None else ""
    if suppress_name or not entry.authors:
        return year
    if policy == "full":
        return f"{', '.join(entry.authors)} {year}".strip()
    return f"{_authors_phrase(entry)} {year}".strip()


def resolve_citations(
    text: str,
    citations: dict[str, Citation],
    bibliography: dict[str, BibEntry],
    policy: str,
    overrides: dict[str, str] | None = None,
) -> str:
    """Replace each marker with its spoken form. `overrides` maps a marker number to a
    pre-validated natural phrase (from the LLM naturalizer); markers without an override
    fall back to the deterministic author-year rendering."""
    overrides = overrides or {}
    if policy == "drop":
        return expand_et_al(_MARKER.sub("", text))

    def replace(match: re.Match[str]) -> str:
        preceding = match.string[: match.start()]
        numbers = [token.strip() for token in match.group(1).split(",") if token.strip()]
        spokens: list[str] = []
        for index, number in enumerate(numbers):
            if number in overrides:
                spokens.append(overrides[number])
                continue
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


def _marker_numbers(text: str) -> list[str]:
    numbers: list[str] = []
    for match in _MARKER.finditer(text):
        numbers += [token.strip() for token in match.group(1).split(",") if token.strip()]
    return numbers


def _marker_preceding(text: str, number: str) -> str:
    """The prose before the first marker that contains `number` (for the inline-author check)."""
    for match in _MARKER.finditer(text):
        if number in (token.strip() for token in match.group(1).split(",")):
            return text[: match.start()]
    return ""


class CitationsStage:
    name = "citations"

    def run(self, doc: Document, ctx: Context) -> Document:
        policy = ctx.config.profile.citation_policy
        overrides = self._naturalize(doc, ctx, policy) if policy != "drop" else {}
        for block in doc.blocks:
            if block.keep and block.handling is Handling.speak:
                block.spoken = resolve_citations(
                    block.current_text(),
                    doc.citations,
                    doc.bibliography,
                    policy,
                    overrides=overrides.get(block.id, {}),
                )
        return doc

    def _naturalize(self, doc: Document, ctx: Context, policy: str) -> dict[str, dict[str, str]]:
        """Per-block {marker: natural phrase} overrides. The model only chooses a STYLE; the
        phrase is rendered deterministically from the author and year, so it can carry no
        content beyond the citation. Inline-author markers are rendered year-only (no double
        name) without consulting the model. A no-op offline (mock LLM -> empty parse) and
        gated on config.curate. An entry with neither author nor year is left to the plain path.
        """
        if not ctx.config.curate:
            return {}
        items: list[dict[str, object]] = []
        entries_by_block: dict[str, dict[str, BibEntry]] = {}
        for block in doc.blocks:
            if not (block.keep and block.handling is Handling.speak):
                continue
            text = block.current_text()
            block_entries: dict[str, BibEntry] = {}
            for number in _marker_numbers(text):
                if number in block_entries:
                    continue
                citation = doc.citations.get(number)
                entry = (
                    doc.bibliography.get(citation.bib_key)
                    if citation and citation.bib_key
                    else None
                )
                if entry is None or not (entry.authors or entry.year is not None):
                    continue
                block_entries[number] = entry
            if block_entries:
                items.append({"id": block.id, "text": text, "markers": list(block_entries)})
                entries_by_block[block.id] = block_entries
        if not items:
            return {}

        styles = self._cached_naturalization(items, ctx)
        overrides: dict[str, dict[str, str]] = {}
        for block in doc.blocks:
            entries = entries_by_block.get(block.id)
            if not entries:
                continue
            text = block.current_text()
            block_styles = styles.get(block.id, {})
            good: dict[str, str] = {}
            for number, entry in entries.items():
                authors = _authors_phrase(entry)
                year = year_to_words(entry.year) if entry.year is not None else ""
                surname = _surname(entry.authors[0]) if entry.authors else ""
                if surname and _author_named_inline(_marker_preceding(text, number), surname):
                    phrase = f"in {year}" if year else None  # author already named; year only
                else:
                    phrase = render_citation(block_styles.get(number, ""), authors, year)
                if phrase:
                    good[number] = phrase
            if good:
                overrides[block.id] = good
        if overrides:
            ctx.log.info("citations_naturalized", blocks=len(overrides))
        return overrides

    def _cached_naturalization(
        self, items: list[dict[str, object]], ctx: Context
    ) -> dict[str, dict[str, str]]:
        payload = f"{NATURALIZE_VERSION}\n{type(ctx.llm).__name__}\n" + json.dumps(
            items, sort_keys=True, ensure_ascii=False
        )
        key = "cite." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_naturalization(cached.decode("utf-8"))
        raw = ctx.llm.complete(build_naturalize_prompt(items))
        parsed = parse_naturalization(raw)
        if parsed:  # never cache an empty/failed parse (e.g. the offline mock)
            ctx.cache.put(key, raw.encode("utf-8"))
        return parsed
