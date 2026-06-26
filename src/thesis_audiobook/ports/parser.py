"""PdfParser port: PDF bytes to a structured Document."""

from __future__ import annotations

from typing import Protocol

from thesis_audiobook.ir import Document


class PdfParser(Protocol):
    def parse(self, pdf_bytes: bytes) -> Document: ...
