"""Stage: citation naturalizer. Treats in-text references as machinery to discard.

For every spoken block it strips the pure reference markers (bracketed [12], bare "word.41",
parenthetical "(Geiger et al., 2009)", a number trailing "et al.") deterministically, then
GENERICIZES narrative author mentions ("Chalmer et al. note that ..." -> "researchers note that
...") so no specific author/year/number is voiced. The genericizing uses ONE cached LLM call per
document that only maps each author mention to a phrase from a fixed set; the substitution is
deterministic, so the claim is never altered. Offline (mock LLM) the genericizing is skipped and a
mention degrades to "Author and others". No bibliography is consulted. The model call + cache live
here; the prompt/parse/apply helpers are pure. Gated on config.curate (the same LLM toggle).
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.citation_naturalize import (
    NATURALIZE_VERSION,
    build_genericize_prompt,
    capitalized_citation_strips,
    find_narrative_mentions,
    naturalize_citations,
    parse_genericization,
    strip_markers,
)
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, Document, Handling
from thesis_audiobook.warnings import LowConfidence

_GENERICIZE_MAX_TOKENS = 4096


class CitationsStage:
    name = "citations"

    def run(self, doc: Document, ctx: Context) -> Document:
        spoken = [b for b in doc.blocks if b.keep and b.handling is Handling.speak]
        mapping = self._genericize(spoken, ctx)
        ctx.citation_genericizations = mapping  # recorded in the ledger
        for block in spoken:
            for span in capitalized_citation_strips(block.current_text()):
                ctx.warnings.add(
                    LowConfidence(
                        block_id=block.id,
                        reason=(
                            f"citation strip removed numbers after capitalized '{span}'; "
                            "verify it is a citation, not a code/cultivar/part series"
                        ),
                        score=0.5,
                    )
                )
            block.spoken = naturalize_citations(block.current_text(), mapping)
        return doc

    def _genericize(self, blocks: list[Block], ctx: Context) -> dict[str, str]:
        """One cached LLM call mapping each distinct narrative author mention -> a generic phrase.
        Returns {} offline or when there is nothing to genericize, so the markers are still
        stripped deterministically and mentions read as 'Author and others'."""
        if not ctx.config.curate:
            return {}
        mentions: dict[str, None] = {}
        for block in blocks:
            for mention in find_narrative_mentions(strip_markers(block.current_text())):
                mentions.setdefault(mention, None)
        if not mentions:
            return {}
        ordered = list(mentions)
        payload = f"{NATURALIZE_VERSION}\n{type(ctx.llm).__name__}\n" + "\n".join(ordered)
        key = "citegeneric." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_genericization(cached.decode("utf-8"))
        raw = ctx.llm.complete(build_genericize_prompt(ordered), max_tokens=_GENERICIZE_MAX_TOKENS)
        mapping = parse_genericization(raw)
        if mapping:  # never cache an empty/failed parse (e.g. the offline mock)
            ctx.cache.put(key, raw.encode("utf-8"))
        return mapping
