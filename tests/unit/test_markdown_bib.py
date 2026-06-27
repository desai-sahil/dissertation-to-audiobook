from __future__ import annotations

from thesis_audiobook.markdown_bib import parse_markdown_bibliography
from thesis_audiobook.stages.citations import resolve_citations

_MD = """\
### CHAPTER 1

### **INTRODUCTION**

Water moves down gradients [1, 2].

## **Bibliography**

- [1] P S Nobel. *Physicochemical and environmental plant physiology*. 1999.
- [2] Mohammed D. Aminu, Seyed Ali Nabavi, and Vasilije Manovic. A review of CO2 storage. \
*Applied Energy*, 208, 2017.

### CHAPTER 2

### **2.1 Introduction**

Crystallization matters [1].

## **Bibliography**

- [1] George W. Scherer. Crystallization in pores. *Cement and Concrete*, 29, 1999.
"""


def test_parses_per_chapter_entries_with_authors_and_years() -> None:
    result = parse_markdown_bibliography(_MD)
    # Chapter-scoped keys, numbering restarts per chapter.
    assert set(result.bibliography) == {"1:1", "1:2", "2:1"}
    assert result.bibliography["1:1"].authors == ["P S Nobel"]
    assert result.bibliography["1:1"].year == 1999
    assert result.bibliography["1:2"].authors == [
        "Mohammed D. Aminu",
        "Seyed Ali Nabavi",
        "Vasilije Manovic",
    ]
    assert result.bibliography["1:2"].year == 2017
    # "1" in chapter 2 is a DIFFERENT reference than "1" in chapter 1.
    assert result.bibliography["2:1"].authors == ["George W. Scherer"]
    assert result.citations["2:1"].bib_key == "2:1"


def test_resolve_uses_chapter_scoped_numbering() -> None:
    result = parse_markdown_bibliography(_MD)
    cites, bib = result.citations, result.bibliography
    # Marker [1] in chapter 1 -> Nobel; the SAME [1] in chapter 2 -> Scherer.
    ch1 = resolve_citations("Water moves [1].", cites, bib, "brief", chapter=1)
    ch2 = resolve_citations("Crystallization [1].", cites, bib, "brief", chapter=2)
    assert "Nobel" in ch1 and "nineteen ninety-nine" in ch1
    assert "Scherer" in ch2 and "Nobel" not in ch2


def test_resolve_brief_groups_and_others() -> None:
    result = parse_markdown_bibliography(_MD)
    out = resolve_citations(
        "As shown [1, 2].", result.citations, result.bibliography, "brief", chapter=1
    )
    assert "Nobel" in out and "Aminu and others" in out  # 3+ authors -> "and others"


def test_empty_markdown_is_empty_bibresult() -> None:
    result = parse_markdown_bibliography("# Just a heading\n\nNo references here.\n")
    assert not result.bibliography and not result.citations
