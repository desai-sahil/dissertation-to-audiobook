"""Stage: content selection and filtering, driven by the profile.

Sets `keep` and `handling` on every block. M1 voices headings and paragraphs.
Front/back matter, the raw bibliography block, footnotes, and code are skipped.
Figure captions are skipped in reading order (the figures stage voices them at the
first in-text reference instead). Display equations and tables are kept; the math and
figures stages voice them per profile (gloss/announce, summarize/skip). The
committee-vs-general difference comes from citation policy plus equation/table handling.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import BlockType, Document, Handling

_SPOKEN_TYPES = {BlockType.heading, BlockType.paragraph}
_SKIP_TYPES = {
    BlockType.frontmatter,
    BlockType.reference_list,
    BlockType.footnote,
    BlockType.code,
    BlockType.figure_caption,
    BlockType.equation_inline,
}


class SelectStage:
    name = "select"

    def run(self, doc: Document, ctx: Context) -> Document:
        profile = ctx.config.profile
        for block in doc.blocks:
            if block.type in _SPOKEN_TYPES:
                block.keep = True
                block.handling = Handling.speak
            elif block.type is BlockType.table:
                # Kept; the figures stage summarizes (committee) or notes-and-skips (general).
                block.keep = True
                block.handling = (
                    Handling.summarize if profile.table_handling == "summarize" else Handling.skip
                )
            elif block.type is BlockType.equation_display:
                # Kept; the math stage announces it by number (no formula read aloud).
                block.keep = True
                block.handling = Handling.announce
            elif block.type is BlockType.backmatter:
                block.keep = profile.include_appendices
                block.handling = Handling.speak if profile.include_appendices else Handling.skip
            elif block.type in _SKIP_TYPES:
                block.keep = False
                block.handling = Handling.skip
        return doc
