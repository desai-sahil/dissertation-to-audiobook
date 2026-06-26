"""Stage: text normalizer for TTS.

Applies the deterministic rules engine to every kept, speakable block, reading the
citation-resolved text left by the citations stage and writing the fully spoken form.
The block's source `text` is never overwritten.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document, Handling
from thesis_audiobook.normalization import normalize_all


class NormalizeStage:
    name = "normalize"

    def run(self, doc: Document, ctx: Context) -> Document:
        for block in doc.blocks:
            if block.keep and block.handling is Handling.speak:
                block.spoken = normalize_all(block.current_text(), ctx.lexicon)
        return doc
