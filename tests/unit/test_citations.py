from __future__ import annotations

from thesis_audiobook.ir import BibEntry, Citation
from thesis_audiobook.stages.citations import (
    expand_et_al,
    resolve_citations,
    spoken_citation,
)

_CITATIONS = {
    "1": Citation(marker="1", bib_key="smith"),
    "2": Citation(marker="2", bib_key="jones"),
    "3": Citation(marker="3", bib_key="lee"),
}
_BIB = {
    "smith": BibEntry(key="smith", authors=["Smith", "Roe"], year=2019),
    "jones": BibEntry(key="jones", authors=["Jones"], year=2020),
    "lee": BibEntry(key="lee", authors=["Lee", "Park", "Kim"], year=2021),
}


def test_brief_two_authors() -> None:
    assert spoken_citation(_BIB["smith"], "brief") == "Smith and Roe twenty nineteen"


def test_brief_three_or_more_authors_says_and_others() -> None:
    assert spoken_citation(_BIB["lee"], "brief") == "Lee and others twenty twenty-one"


def test_brief_single_author() -> None:
    assert spoken_citation(_BIB["jones"], "brief") == "Jones twenty twenty"


def test_full_lists_all_authors() -> None:
    assert spoken_citation(_BIB["lee"], "full") == "Lee, Park, Kim twenty twenty-one"


def test_resolve_brief_inline() -> None:
    assert (
        resolve_citations("we found x [1].", _CITATIONS, _BIB, "brief")
        == "we found x Smith and Roe twenty nineteen."
    )


def test_resolve_drop_removes_marker() -> None:
    assert resolve_citations("we found x [1].", _CITATIONS, _BIB, "drop") == "we found x."


def test_resolve_group() -> None:
    assert (
        resolve_citations("see [2, 3].", _CITATIONS, _BIB, "brief")
        == "see Jones twenty twenty; Lee and others twenty twenty-one."
    )


def test_unknown_marker_is_dropped() -> None:
    assert resolve_citations("x [99].", {}, {}, "brief") == "x."


def test_marker_with_unlinked_bibentry_is_dropped() -> None:
    # Marker resolves to a bib_key, but that key is absent from the bibliography.
    citations = {"1": Citation(marker="1", bib_key="ghost")}
    assert resolve_citations("x [1].", citations, {}, "brief") == "x."


def test_expand_et_al() -> None:
    assert expand_et_al("Bacheva et al. showed") == "Bacheva and others showed"
