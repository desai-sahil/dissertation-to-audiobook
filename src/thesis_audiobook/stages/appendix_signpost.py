"""Stage: appendix cross-reference signpost.

Runs after the spoken text is finalized (post-normalize) and before assemble_script, so the
fixed aside is part of the script. Pure logic lives in appendix_signpost.py; this stage just
reads the profile and applies it. No I/O.
"""

from __future__ import annotations

from thesis_audiobook.appendix_signpost import apply_signposts
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document


class AppendixSignpostStage:
    name = "appendix_signpost"

    def run(self, doc: Document, ctx: Context) -> Document:
        count = apply_signposts(
            doc.blocks, include_appendices=ctx.config.profile.include_appendices
        )
        if count:
            ctx.log.info("appendix_signposts", count=count)
        return doc
