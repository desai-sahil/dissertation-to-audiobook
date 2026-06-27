"""Parse a Marker markdown's per-chapter reference lists into a BibResult. Pure, no I/O.

A stapled-papers thesis restarts citation numbering each chapter, so the inline [n] markers
and the reference entries are CHAPTER-SCOPED. We key both the bibliography and the citations
by "<chapter>:<number>"; the CitationsStage resolves a marker [n] in a chapter-C block by
trying "C:n" first (and falls back to the bare "n" for a globally-numbered thesis, so the
poppler/GROBID path is unaffected).

Entries are markdown list items: "- [1] Authors. *Title*. ... 2019." Author/year extraction
is a best-effort heuristic - references are skipped from the audio, so this only feeds the
inline "Author, year" citation rendering, and the naturalizer drops anything missing both.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import BibEntry, Citation
from thesis_audiobook.ports.bib import BibResult

# A chapter heading: "### CHAPTER 2" (requires the word CHAPTER so "## 2.1 Methods" is not one).
_CHAPTER_HEAD = re.compile(r"^#+\s*\**\s*CHAPTER\s+(\d+)\b", re.IGNORECASE)
# An appendix heading resets the chapter so appendix reference lists (skipped from audio) are
# not mis-attributed to the last chapter.
_APPENDIX_HEAD = re.compile(r"^#+\s*\**\s*APPENDIX\b", re.IGNORECASE)
_BIB_HEAD = re.compile(r"^#+\s*\**\s*(?:bibliography|references)\b", re.IGNORECASE)
_HEAD = re.compile(r"^#+\s")
_ENTRY = re.compile(r"^[-*]?\s*\[(\d+)\]\s+(.+)$")
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
_WORD = re.compile(r"[A-Za-z]+")


def _author_segment(entry: str) -> str:
    """The author-list portion of a reference: text up to the first sentence boundary whose
    preceding word is a surname (>= 3 letters), so initials like 'D.' or 'Th.' do not end it."""
    for match in re.finditer(r"\.\s", entry):
        words = _WORD.findall(entry[: match.start()])
        if words and len(words[-1]) >= 3:
            return entry[: match.start()].strip()
    return entry.split(". ")[0].strip()


def _split_authors(segment: str) -> list[str]:
    segment = segment.replace("*", "").replace("_", "")
    parts = [part.strip(" ,.") for part in re.split(r",| and ", segment)]
    return [part for part in parts if part]


def _parse_entry(rest: str) -> tuple[list[str], int | None]:
    years = _YEAR.findall(rest)
    year = int(years[-1]) if years else None
    return _split_authors(_author_segment(rest)), year


def parse_markdown_bibliography(markdown: str) -> BibResult:
    bibliography: dict[str, BibEntry] = {}
    citations: dict[str, Citation] = {}
    chapter: int | None = None
    in_bib = False

    for line in markdown.splitlines():
        chapter_match = _CHAPTER_HEAD.match(line)
        if chapter_match is not None:
            chapter = int(chapter_match.group(1))
            in_bib = False
            continue
        if _APPENDIX_HEAD.match(line):
            chapter = None  # appendix bibliographies are skipped, not attributed to a chapter
            in_bib = False
            continue
        if _BIB_HEAD.match(line):
            in_bib = True
            continue
        if _HEAD.match(line):  # any other heading closes the reference list
            in_bib = False
            continue
        if not (in_bib and chapter is not None):
            continue
        entry = _ENTRY.match(line.strip())
        if entry is None:
            continue
        number, rest = entry.group(1), entry.group(2)
        key = f"{chapter}:{number}"
        if key in bibliography:
            continue
        authors, year = _parse_entry(rest)
        bibliography[key] = BibEntry(key=key, authors=authors, year=year)
        citations[key] = Citation(marker=number, bib_key=key)

    return BibResult(bibliography=bibliography, citations=citations)
