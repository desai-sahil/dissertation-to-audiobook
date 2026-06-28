"""Stage: assign each block its physical page (v2 engine), for vision escalation.

Fills block.page from the PDF's per-page text (ctx.page_texts, extracted by the CLI edge via
poppler) for any block Marker did not already anchor - so the vision page-image fallback can locate
a held block whether or not this thesis's Marker run emitted page anchors. Pure (the poppler I/O is
at the edge); no-op unless engine == 'v2' and page texts are present.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document
from thesis_audiobook.page_align import assign_pages_by_text


class PageAlignStage:
    name = "page_align"

    def run(self, doc: Document, ctx: Context) -> Document:
        if ctx.config.engine != "v2" or not doc.blocks or not ctx.page_texts:
            return doc
        assigned = assign_pages_by_text(doc.blocks, ctx.page_texts)
        if assigned:
            ctx.log.info("page_aligned", assigned=assigned, blocks=len(doc.blocks))
        return doc
