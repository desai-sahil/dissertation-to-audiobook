from __future__ import annotations

from thesis_audiobook.ir import BibEntry, Block, BlockType, Citation, Document, DocumentMeta
from thesis_audiobook.linkage import body_markers, citation_linkage


def _doc(text: str, citations: dict[str, Citation], bibliography: dict[str, BibEntry]) -> Document:
    return Document(
        meta=DocumentMeta(title="t"),
        blocks=[Block(id="p", type=BlockType.paragraph, text=text)],
        citations=citations,
        bibliography=bibliography,
    )


def test_body_markers_extracts_groups() -> None:
    doc = _doc("see [1] and [2, 3] but not refs", {}, {})
    assert body_markers(doc) == {"1", "2", "3"}


def test_full_linkage() -> None:
    doc = _doc(
        "see [1] and [2, 3].",
        {n: Citation(marker=n, bib_key=n) for n in ("1", "2", "3")},
        {n: BibEntry(key=n) for n in ("1", "2", "3")},
    )
    rate, resolved, unresolved = citation_linkage(doc)
    assert rate == 1.0
    assert resolved == ["1", "2", "3"]
    assert unresolved == []


def test_linkage_reports_misses() -> None:
    doc = _doc(
        "see [1] and [9].", {"1": Citation(marker="1", bib_key="a")}, {"a": BibEntry(key="a")}
    )
    rate, resolved, unresolved = citation_linkage(doc)
    assert resolved == ["1"]
    assert unresolved == ["9"]
    assert rate == 0.5
