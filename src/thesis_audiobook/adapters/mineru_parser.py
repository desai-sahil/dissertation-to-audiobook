"""MinerU PdfParser adapter: the equation-heavy alternative to Marker, same port.

MinerU has the strongest LaTeX formula recovery; use it when Marker's math output is
weak. Imported lazily, with a clear typed error if unavailable. Shares the pure
markdown-to-IR step with the Marker adapter.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from thesis_audiobook.ir import Document
from thesis_audiobook.markdown_ir import markdown_to_document


class MinerUUnavailableError(RuntimeError):
    """The MinerU CLI is not installed."""


class MinerUParser:
    def __init__(self, *, title: str | None = None) -> None:
        self._title = title

    def parse(self, pdf_bytes: bytes) -> Document:
        markdown = self._to_markdown(pdf_bytes)
        return markdown_to_document(markdown, title=self._title)

    def _to_markdown(self, pdf_bytes: bytes) -> str:
        import shutil

        executable = shutil.which("mineru")
        if executable is None:  # pragma: no cover - exercised only live
            raise MinerUUnavailableError(
                "MinerU is not installed. Install it (pip install mineru) "
                "or run with --parser poppler."
            )
        with tempfile.TemporaryDirectory() as directory:  # pragma: no cover - live only
            base = Path(directory)
            source = base / "input.pdf"
            source.write_bytes(pdf_bytes)
            out_dir = base / "out"
            subprocess.run(
                [executable, "-p", str(source), "-o", str(out_dir), "-m", "auto"],
                capture_output=True,
                check=True,
            )
            markdown_files = list(out_dir.rglob("*.md"))
            if not markdown_files:
                raise MinerUUnavailableError("MinerU produced no markdown output")
            return markdown_files[0].read_text(encoding="utf-8")
