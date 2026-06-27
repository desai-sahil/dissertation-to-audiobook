"""MarkdownBibParser: chapter-scoped bibliography + citation linkage from a markdown file.

The BibParser counterpart of MarkdownFileParser - reads the same standalone-Marker markdown
and extracts its per-chapter reference lists (see markdown_bib.parse_markdown_bibliography).
The parsing is pure; this adapter only reads the file.
"""

from __future__ import annotations

from pathlib import Path

from thesis_audiobook.markdown_bib import parse_markdown_bibliography
from thesis_audiobook.ports.bib import BibResult


class MarkdownBibParser:
    def __init__(self, md_path: str | Path) -> None:
        self._path = Path(md_path)

    def parse(self, pdf_bytes: bytes) -> BibResult:
        # pdf_bytes ignored: the references come from the pre-parsed markdown.
        if not self._path.exists():
            return BibResult(bibliography={}, citations={})
        return parse_markdown_bibliography(self._path.read_text(encoding="utf-8"))
