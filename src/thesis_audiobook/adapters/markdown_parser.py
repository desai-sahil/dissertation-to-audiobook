"""MarkdownFileParser: ingest a pre-parsed markdown file as the IR source.

Decouples heavy ML parsers (Marker, MinerU) from this project's environment. Run the
parser as a STANDALONE tool - e.g. `marker_single thesis.pdf --output_dir out/` - then
feed the resulting markdown here with `--parser markdown --markdown out/thesis.md`. This
sidesteps marker-pdf's hard `anthropic<0.47` pin, which conflicts with the anthropic
version this project needs for Claude. The markdown->IR step is the same pure function the
in-process MarkerParser uses, so the downstream pipeline is identical.
"""

from __future__ import annotations

from pathlib import Path

from thesis_audiobook.ir import Document
from thesis_audiobook.markdown_ir import markdown_to_document


class MarkdownFileUnavailableError(RuntimeError):
    """The markdown file to ingest does not exist."""


class MarkdownFileParser:
    def __init__(self, md_path: str | Path, *, title: str | None = None) -> None:
        self._path = Path(md_path)
        self._title = title

    def parse(self, pdf_bytes: bytes) -> Document:
        # pdf_bytes is ignored: the structure comes from the pre-parsed markdown.
        if not self._path.exists():
            raise MarkdownFileUnavailableError(f"markdown file not found: {self._path}")
        text = self._path.read_text(encoding="utf-8")
        return markdown_to_document(text, title=self._title)
