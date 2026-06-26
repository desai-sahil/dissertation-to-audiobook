"""BibParser port: bibliography parsing plus inline-citation linkage."""

from __future__ import annotations

from typing import Protocol

from thesis_audiobook.ir import BibEntry, Citation, StrictModel


class BibResult(StrictModel):
    bibliography: dict[str, BibEntry]
    citations: dict[str, Citation]


class BibParser(Protocol):
    def parse(self, pdf_bytes: bytes) -> BibResult: ...
