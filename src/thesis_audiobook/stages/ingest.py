"""Stage: ingest and parse.

Pulls the structured Document from the parser port and merges the bibliography port's
output (the GROBID, or poppler-fallback, citation map) into the IR. The build_ir stage
then cleans the result. The parser/bib adapters are wired by bootstrap.build_context.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document


class IngestStage:
    name = "ingest"

    def run(self, doc: Document, ctx: Context) -> Document:
        parsed = ctx.parser.parse(ctx.pdf_bytes)
        bib = ctx.bib.parse(ctx.pdf_bytes)
        parsed.bibliography.update(bib.bibliography)
        parsed.citations.update(bib.citations)
        return parsed
