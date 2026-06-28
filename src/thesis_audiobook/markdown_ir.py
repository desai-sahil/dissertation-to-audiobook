"""Pure markdown-to-IR conversion shared by the Marker and MinerU adapters. No I/O.

Marker and MinerU both render a PDF to markdown; this turns that markdown into raw IR
blocks. It is deterministic and unit-testable against a committed sample of the
parser's output, so the adapters' output handling is covered offline even though the
parsers themselves only run under the live integration test.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.normalization.latex import split_display_math

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_SECTION = re.compile(r"^(\d+(?:\.\d+)+)\s+(.*)$")  # a dotted section number: "2.3.1 Title"
_SINGLE_SECTION = re.compile(r"^(\d+)\s+(\S.*)$")  # a bare integer section: "2 Background"
# A TRUE chapter divider, the one cross-thesis anchor: the heading text is exactly "CHAPTER N"
# (Marker emits it at whatever level - Gao #### , Jain ### ). A bare numbered heading like
# "# 2 Background" is a SECTION, never a chapter; only this explicit divider sets the chapter.
_DIVIDER = re.compile(r"(?i)^chapter\s+(\d+)$")
_APPENDIX = re.compile(r"(?i)^appendix\b")  # an appendix heading (after any number/letter strip)
_IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\([^)]*\)\s*$")
# Marker marks each new page with an empty anchor span, <span id="page-N-M"></span> (N is its
# 0-indexed page). We read N to set block.page (1-indexed physical, matching the rendered pages the
# vision passes see), and strip ALL span tags so they never pollute a heading's text or leak into
# narration (the v1 "span id ... page nine" read-aloud bug).
_PAGE_ANCHOR = re.compile(r'<span\s+id="page-(\d+)-\d+"\s*>\s*</span>')
_SPAN = re.compile(r"</?span[^>]*>")


def _is_table(lines: list[str]) -> bool:
    rows = [line for line in lines if line.strip()]
    return len(rows) >= 2 and all(row.strip().startswith("|") for row in rows)


def _looks_like_name(text: str) -> str | None:
    """The text if it reads like a name (2-4 words, capitalized ends, no digits), else None."""
    words = text.split()
    if not (2 <= len(words) <= 4) or any(c.isdigit() for c in text):
        return None
    if words[0][:1].isupper() and words[-1][:1].isupper():
        return text
    return None


def _derive_author(blocks: list[Block]) -> str | None:
    """Pull the author off the title page: the name block right after a standalone 'by', or failing
    that the '(c) <year> <Name>' copyright line. Conservative - returns None rather than guess."""
    for i in range(len(blocks) - 1):
        if blocks[i].text.strip().lower() == "by":
            name = _looks_like_name(blocks[i + 1].text.strip())
            if name:
                return name
    for block in blocks[:20]:
        match = re.search(r"(?:©|\(c\)|copyright)\s*\d{4}\s+(.+)", block.text, re.IGNORECASE)
        if match:
            candidate = re.split(r"\s+all rights", match.group(1), flags=re.IGNORECASE)[0].strip()
            name = _looks_like_name(candidate)
            if name:
                return name
    return None


def _clean_title(content: str) -> str:
    """A thesis title page is often rendered all caps; sentence-case it so it reads and displays
    cleanly. Mixed-case titles are left exactly as the author wrote them (acronyms preserved)."""
    title = " ".join(content.split())
    letters = [c for c in title if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return title[:1].upper() + title[1:].lower()
    return title


def markdown_to_document(markdown: str, *, title: str | None = None) -> Document:
    blocks: list[Block] = []
    chapter: int | None = None
    page: int | None = None
    derived_title: str | None = None
    seq = 0

    for chunk in re.split(r"\n\s*\n", markdown):
        raw = chunk.strip()
        if not raw:
            continue
        for anchor in _PAGE_ANCHOR.finditer(raw):
            page = int(anchor.group(1)) + 1  # 1-indexed physical page
        text = _SPAN.sub("", raw).strip()
        if not text:
            continue  # the chunk was only a page anchor / span tags
        lines = text.split("\n")
        seq += 1
        block_id = f"m{seq}"

        # A standalone $$...$$ chunk is a display equation: keep the LaTeX so the math stage
        # can announce it by number, instead of letting raw LaTeX fall through as a paragraph.
        display = split_display_math(text)
        if display is not None:
            blocks.append(
                Block(
                    id=block_id,
                    type=BlockType.equation_display,
                    chapter=chapter,
                    page=page,
                    text=display,
                    latex=display,
                )
            )
            continue

        heading = _HEADING.match(lines[0]) if len(lines) == 1 else None
        if heading is not None:
            # Strip markdown emphasis before classifying: Marker wraps many headings in **bold**
            # (e.g. Jain's "### **1.2 Thesis Outline**"), and a leading '*' would otherwise hide the
            # section number. Removing it lets _SECTION/_DIVIDER see the number and reads cleaner.
            content = " ".join(heading.group(2).replace("*", "").split())
            # A chapter divider sets the running chapter and is not itself spoken; the next title
            # heading carries the single "Chapter N. Title." announcement. Without this, Gao's
            # per-chapter "# 1.. # 6" section restarts used to clobber the chapter number.
            divider = _DIVIDER.match(content)
            if divider is not None:
                chapter = int(divider.group(1))
                continue
            section: str | None = None
            numbered = False
            section_match = _SECTION.match(content) or _SINGLE_SECTION.match(content)
            if section_match is not None:
                section, content = section_match.group(1), section_match.group(2).strip()
                numbered = True
            # The first un-numbered heading (any level) is the title-page title; capture it so the
            # title never silently falls back to "Untitled Thesis" when the cartographer cannot
            # propose one (e.g. its cache was invalidated by a Structurer reclassification). The
            # block keeps its original text; only the derived title is cleaned.
            if derived_title is None and not numbered:
                derived_title = _clean_title(content)
            blocks.append(
                Block(
                    id=block_id,
                    type=BlockType.heading,
                    chapter=chapter,
                    page=page,
                    section=section,
                    text=content,
                )
            )
            continue

        image = _IMAGE.match(text)
        if image is not None:
            blocks.append(
                Block(
                    id=block_id,
                    type=BlockType.figure_caption,
                    chapter=chapter,
                    page=page,
                    text=image.group("alt").strip(),
                )
            )
            continue

        block_type = BlockType.table if _is_table(lines) else BlockType.paragraph
        flattened = text if block_type is BlockType.table else " ".join(lines)
        blocks.append(
            Block(id=block_id, type=block_type, chapter=chapter, page=page, text=flattened)
        )

    # Appendices (and everything after them, e.g. a trailing bibliography or source-code listing)
    # are back matter: read only when the profile opts in (select gates BlockType.backmatter on
    # include_appendices), and their code never reaches TTS otherwise. Detected by the first
    # APPENDIX heading; the remainder of the document follows it. Deterministic and claim-safe -
    # only block.type changes, no text is edited.
    appendix_at = next(
        (
            i
            for i, b in enumerate(blocks)
            if b.type is BlockType.heading and _APPENDIX.match(b.text)
        ),
        None,
    )
    if appendix_at is not None:
        for block in blocks[appendix_at:]:
            block.type = BlockType.backmatter

    return Document(
        meta=DocumentMeta(
            title=title or derived_title or "Untitled Thesis",
            author=_derive_author(blocks),
        ),
        blocks=blocks,
    )
