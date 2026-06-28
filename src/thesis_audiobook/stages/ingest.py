"""Stage: ingest and parse.

Pulls the structured Document from the parser port. The build_ir stage then cleans the
result. The parser adapter is wired by bootstrap.build_context. Citations are handled later
by the citations stage (genericized, no bibliography), so no bibliography is parsed here.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document


class IngestStage:
    name = "ingest"

    def run(self, doc: Document, ctx: Context) -> Document:
        return ctx.parser.parse(ctx.pdf_bytes)
