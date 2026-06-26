"""Marker PdfParser adapter (primary parser per the spec).

Marker is a local, free, ML-based PDF-to-markdown converter. It is imported lazily so
the package stays importable without the heavy dependency installed; a clear typed
error is raised if it is invoked without being available. The markdown-to-IR step is a
pure function (markdown_ir.markdown_to_document), unit-tested offline; this adapter
only runs under the live integration test.
"""
# The marker-pdf package is optional and untyped; its symbols are unknown to pyright.
# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false

from __future__ import annotations

import tempfile
from pathlib import Path

from thesis_audiobook.ir import Document
from thesis_audiobook.markdown_ir import markdown_to_document


class MarkerUnavailableError(RuntimeError):
    """The marker-pdf package is not installed."""


class MarkerParser:
    def __init__(self, *, title: str | None = None) -> None:
        self._title = title

    def parse(self, pdf_bytes: bytes) -> Document:
        markdown = self._to_markdown(pdf_bytes)
        return markdown_to_document(markdown, title=self._title)

    def _to_markdown(self, pdf_bytes: bytes) -> str:
        try:
            from marker.config.parser import ConfigParser
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered
        except ImportError as error:  # pragma: no cover - exercised only live
            raise MarkerUnavailableError(
                "marker-pdf is not installed. Install it (pip install marker-pdf) "
                "or run with --parser poppler."
            ) from error

        with tempfile.TemporaryDirectory() as directory:  # pragma: no cover - live only
            source = Path(directory) / "input.pdf"
            source.write_bytes(pdf_bytes)
            config_parser = ConfigParser({"output_format": "markdown"})
            converter = PdfConverter(
                artifact_dict=create_model_dict(),
                config=config_parser.generate_config_dict(),
            )
            rendered = converter(str(source))
            markdown, _, _ = text_from_rendered(rendered)
        return markdown
