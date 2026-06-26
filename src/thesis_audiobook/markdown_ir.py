"""Pure markdown-to-IR conversion shared by the Marker and MinerU adapters. No I/O.

Marker and MinerU both render a PDF to markdown; this turns that markdown into raw IR
blocks. It is deterministic and unit-testable against a committed sample of the
parser's output, so the adapters' output handling is covered offline even though the
parsers themselves only run under the live integration test.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_SECTION = re.compile(r"^(\d+(?:\.\d+)+)\s+(.*)$")
_CHAPTER = re.compile(r"^(?:chapter\s+)?(\d+)\.?\s+(.*)$", re.IGNORECASE)
_IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\([^)]*\)\s*$")


def _is_table(lines: list[str]) -> bool:
    rows = [line for line in lines if line.strip()]
    return len(rows) >= 2 and all(row.strip().startswith("|") for row in rows)


def markdown_to_document(markdown: str, *, title: str | None = None) -> Document:
    blocks: list[Block] = []
    chapter: int | None = None
    seq = 0

    for chunk in re.split(r"\n\s*\n", markdown):
        text = chunk.strip()
        if not text:
            continue
        lines = text.split("\n")
        seq += 1
        block_id = f"m{seq}"

        heading = _HEADING.match(lines[0]) if len(lines) == 1 else None
        if heading is not None:
            level, content = len(heading.group(1)), heading.group(2).strip()
            section: str | None = None
            section_match = _SECTION.match(content)
            if section_match is not None:
                section, content = section_match.group(1), section_match.group(2).strip()
            elif level == 1:
                chapter_match = _CHAPTER.match(content)
                if chapter_match is not None:
                    chapter = int(chapter_match.group(1))
                    content = chapter_match.group(2).strip() or content
            blocks.append(
                Block(
                    id=block_id,
                    type=BlockType.heading,
                    chapter=chapter,
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
                    text=image.group("alt").strip(),
                )
            )
            continue

        block_type = BlockType.table if _is_table(lines) else BlockType.paragraph
        flattened = text if block_type is BlockType.table else " ".join(lines)
        blocks.append(Block(id=block_id, type=block_type, chapter=chapter, text=flattened))

    return Document(meta=DocumentMeta(title=title or "Untitled Thesis"), blocks=blocks)
