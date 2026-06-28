from __future__ import annotations

from pathlib import Path

from thesis_audiobook.ir import BlockType
from thesis_audiobook.markdown_ir import markdown_to_document


def test_markdown_to_document(cassette_dir: Path) -> None:
    markdown = (cassette_dir / "marker_sample.md").read_text(encoding="utf-8")
    doc = markdown_to_document(markdown, title="Sample")
    types = [block.type for block in doc.blocks]

    assert doc.meta.title == "Sample"
    assert BlockType.heading in types
    assert BlockType.paragraph in types
    assert BlockType.figure_caption in types
    assert BlockType.table in types

    sections = {block.section for block in doc.blocks if block.section}
    assert {"6.1", "6.2"} <= sections

    captions = [b.text for b in doc.blocks if b.type is BlockType.figure_caption]
    assert captions == ["Figure 1. Gas exchange over time."]


def test_title_derived_from_first_unnumbered_heading_sentence_cased() -> None:
    # The title page (an all-caps H1, as Marker renders it) becomes the title, sentence-cased.
    md = "# STUDY OF IN-PLANT SENSING IN AGRICULTURE\n\n#### A Thesis\n\n## 1 Introduction\n"
    doc = markdown_to_document(md)
    assert doc.meta.title == "Study of in-plant sensing in agriculture"
    # the block itself keeps its original casing (so the cartographer's verbatim check still works)
    assert doc.blocks[0].text == "STUDY OF IN-PLANT SENSING IN AGRICULTURE"


def test_title_derived_from_level_two_heading() -> None:
    # Some theses (Jain) render the title as an H2, not H1 - any un-numbered heading qualifies.
    md = "## TRANSDUCING THERMODYNAMIC STATE OF WATER\n\n### A Dissertation\n"
    assert markdown_to_document(md).meta.title == "Transducing thermodynamic state of water"


def test_explicit_title_wins_and_numbered_headings_are_not_titles() -> None:
    # A caller-supplied title beats the derived one.
    md = "# 1 Introduction\n\n## 1.1 Background\n"
    assert markdown_to_document(md, title="Override").meta.title == "Override"
    # With no title page and only numbered headings, nothing is mistaken for the title.
    assert markdown_to_document(md).meta.title == "Untitled Thesis"


def test_mixed_case_title_is_left_as_written() -> None:
    md = "# The µTM and WUE in Apple\n"
    assert markdown_to_document(md).meta.title == "The µTM and WUE in Apple"


def _by_text(doc, needle: str):
    return next(b for b in doc.blocks if needle in b.text)


def test_chapter_divider_sets_chapter_and_is_not_emitted() -> None:
    # "CHAPTER 1" (at whatever level Marker used) sets the running chapter and is itself dropped;
    # the next title heading carries the single "Chapter one." announcement.
    md = "#### CHAPTER 1\n\n#### INTRODUCTION\n\n# 1 Context and Motivation\n"
    doc = markdown_to_document(md)
    assert all(b.text.upper() != "CHAPTER 1" for b in doc.blocks)  # divider not emitted
    intro = _by_text(doc, "INTRODUCTION")
    assert intro.chapter == 1 and intro.section is None  # the chapter title carries the number
    ctx = _by_text(doc, "Context and Motivation")
    assert ctx.section == "1" and ctx.chapter == 1  # a bare "# N" is a SECTION, not a chapter


def test_per_chapter_section_restart_does_not_clobber_chapter() -> None:
    # The Gao trap: "# 1".. "# 6" sections restart inside each chapter. A bare numeric heading must
    # NOT become a chapter, so the next real divider's number reaches its title (not the stale 6).
    md = (
        "#### CHAPTER 2\n\n#### MATERIALS AND METHODS\n\n"
        "# 1 Introduction\n\n# 6 Conclusion\n\n"
        "#### CHAPTER 3\n\n#### RESULTS AND DISCUSSION\n"
    )
    doc = markdown_to_document(md)
    assert _by_text(doc, "Conclusion").section == "6"  # a section, chapter stays 2
    assert _by_text(doc, "Introduction").chapter == 2
    results = _by_text(doc, "RESULTS AND DISCUSSION")
    assert results.chapter == 3 and results.section is None  # NOT 6


def test_emphasis_wrapped_section_number_is_detected() -> None:
    # Jain wraps headings in **bold**; the leading '*' must not hide the section number.
    doc = markdown_to_document("### **1.2 Thesis Outline**\n")
    block = doc.blocks[0]
    assert block.section == "1.2" and block.text == "Thesis Outline"


def test_page_anchors_set_block_page_and_spans_are_stripped() -> None:
    # Marker marks each page with <span id="page-N-M"></span> (0-indexed N). We read it into
    # block.page (1-indexed physical) and strip the span so it never leaks into a heading/narration.
    md = (
        '<span id="page-9-0"></span>#### **I. INTRODUCTION**\n\n'
        '<span id="page-9-1"></span>First paragraph of the chapter.\n\n'
        "Continued prose, no anchor of its own.\n\n"
        '<span id="page-10-0"></span>A paragraph on the next page.\n'
    )
    doc = markdown_to_document(md)
    assert all("<span" not in b.text for b in doc.blocks)  # every span stripped
    intro = _by_text(doc, "INTRODUCTION")
    assert intro.text == "I. INTRODUCTION" and intro.page == 10  # 0-indexed 9 -> physical page 10
    assert _by_text(doc, "First paragraph").page == 10
    assert _by_text(doc, "Continued prose").page == 10  # carried forward (no anchor)
    assert _by_text(doc, "next page").page == 11


def test_author_from_standalone_by_line() -> None:
    # The title page: a standalone "by" then the name block. The name (not the degree/date that
    # follows) becomes meta.author, which the intro reads as "..., by <Author>.".
    md = (
        "# A TITLE PAGE\n\nA Dissertation Presented to the Faculty\n\n"
        "by\n\nPiyush Jain\n\nAugust 2023\n\nSome opening prose of the abstract.\n"
    )
    assert markdown_to_document(md).meta.author == "Piyush Jain"


def test_author_falls_back_to_copyright_line() -> None:
    # No standalone "by", but a "(c) <year> <Name> ALL RIGHTS RESERVED" line: take the name only.
    md = "# A TITLE\n\nFront matter.\n\n© 2020 Rui Gao ALL RIGHTS RESERVED\n\nAbstract prose.\n"
    assert markdown_to_document(md).meta.author == "Rui Gao"


def test_author_is_none_when_not_a_name() -> None:
    # Conservative: a "by" followed by something that is not name-shaped yields no author, rather
    # than narrating a wrong "by ...". The intro then simply omits the clause.
    md = "# A TITLE\n\nby\n\nthe Graduate School of Cornell University\n\nAbstract prose here.\n"
    assert markdown_to_document(md).meta.author is None


def test_appendix_and_everything_after_is_backmatter() -> None:
    md = (
        "#### CHAPTER 4\n\n#### CONCLUSION\n\nSome closing prose.\n\n"
        "# 5 APPENDIX\n\nimport numpy as np\n\n#### BIBLIOGRAPHY\n\n[1] A. Author, 2020.\n"
    )
    doc = markdown_to_document(md)
    assert _by_text(doc, "closing prose").type is BlockType.paragraph  # body untouched
    assert _by_text(doc, "APPENDIX").type is BlockType.backmatter
    assert _by_text(doc, "import numpy").type is BlockType.backmatter  # appendix code skipped
    assert _by_text(doc, "A. Author").type is BlockType.backmatter  # trailing bib too
