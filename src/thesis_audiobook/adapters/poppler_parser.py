"""Pure-Python PDF parser built on poppler's pdftotext. Runs offline, no ML, no network.

This is the hybrid-plan fallback that lets the whole pipeline run and be tested
without Marker/MinerU. It implements the PdfParser port. The pdftotext subprocess is
the only I/O; the text-to-IR parsing is the pure module function parse_document, which
is contract-tested offline against a recorded pdftotext cassette.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta

_CHAPTER = re.compile(r"^CHAPTER\s+(\d+)$", re.IGNORECASE)
_SECTION_NUM = re.compile(r"^(\d+(?:\.\d+)+)$")
_SECTION_INLINE = re.compile(r"^(\d+(?:\.\d+)+)\s+(\S.*)$")
_PAGE_NUM = re.compile(r"^\d{1,4}$")
_REF_START = re.compile(r"^\[(\d+)\]\s+(.*)$")


class PopplerUnavailableError(RuntimeError):
    """pdftotext (poppler) is not installed or failed."""


def pdftotext(pdf_bytes: bytes, *, layout: bool = False) -> str:
    """Run poppler's pdftotext over PDF bytes (the only I/O in this module)."""
    executable = shutil.which("pdftotext")
    if executable is None:
        raise PopplerUnavailableError("pdftotext (poppler) is not installed")
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "input.pdf"
        source.write_bytes(pdf_bytes)
        args = [executable, *(["-layout"] if layout else []), str(source), "-"]
        try:
            completed = subprocess.run(args, capture_output=True, check=True)
        except subprocess.CalledProcessError as error:  # pragma: no cover - defensive
            raise PopplerUnavailableError(f"pdftotext failed: {error}") from error
    return completed.stdout.decode("utf-8", errors="replace")


def _next_nonblank(lines: list[str], start: int) -> tuple[str, int]:
    index = start
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines):
        return lines[index].strip(), index + 1
    return "", index


def _titlecase(text: str) -> str:
    return text.title() if text.isupper() else text


def parse_document(text: str, *, title: str | None = None) -> Document:
    """Pure: turn pdftotext reflow output into raw IR blocks. build_ir cleans further."""
    pages = text.split("\f")
    blocks: list[Block] = []
    chapter: int | None = None
    chapter_title = ""
    seq = 0

    def emit(block_type: BlockType, body: str, page: int, section: str | None = None) -> None:
        nonlocal seq
        seq += 1
        blocks.append(
            Block(
                id=f"b{seq}",
                type=block_type,
                chapter=chapter,
                section=section,
                page=page,
                text=body,
            )
        )

    for page_no, page in enumerate(pages, start=1):
        lines = page.split("\n")
        buffer: list[str] = []

        def flush(page: int = page_no) -> None:
            nonlocal buffer
            joined = " ".join(buffer).strip()
            if joined:
                block_type = (
                    BlockType.reference_list if joined.startswith("[") else BlockType.paragraph
                )
                emit(block_type, joined, page)
            buffer = []

        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line:
                flush()
                index += 1
                continue
            if _PAGE_NUM.match(line):
                flush()
                emit(BlockType.paragraph, line, page_no)  # build_ir strips this
                index += 1
                continue
            chapter_match = _CHAPTER.match(line)
            if chapter_match:
                flush()
                chapter = int(chapter_match.group(1))
                heading_title, index = _next_nonblank(lines, index + 1)
                chapter_title = _titlecase(heading_title) or f"Chapter {chapter}"
                emit(BlockType.heading, chapter_title, page_no)
                continue
            section_inline = _SECTION_INLINE.match(line)
            if section_inline:
                flush()
                emit(BlockType.heading, section_inline.group(2), page_no, section_inline.group(1))
                index += 1
                continue
            section_num = _SECTION_NUM.match(line)
            if section_num:
                flush()
                number = section_num.group(1)
                heading_title, index = _next_nonblank(lines, index + 1)
                emit(BlockType.heading, heading_title or number, page_no, number)
                continue
            if _REF_START.match(line) and buffer and not buffer[0].startswith("["):
                flush()
            buffer.append(line)
            index += 1
        flush()

    return Document(
        meta=DocumentMeta(title=title or chapter_title or "Untitled Thesis"), blocks=blocks
    )


class PopplerParser:
    """PdfParser via pdftotext reflow."""

    def parse(self, pdf_bytes: bytes) -> Document:
        return parse_document(pdftotext(pdf_bytes))
