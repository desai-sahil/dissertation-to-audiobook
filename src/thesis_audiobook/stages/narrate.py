"""Stage: verifier-gated narrator (v2 engine).

Maps the vision structure map onto the IR blocks, narrates each read prose block through the
generator (text model via the LlmClient port), and records the (source, spoken) pairs + the
flagged-for-review segments on ctx. No-op unless engine == 'v2'.

COST SAFETY: every model call is content-addressed CACHED here, so a re-run re-bills nothing and a
single edit re-narrates only the changed block; the generator itself is hard-capped per segment
(see engine.py / narrate.py). Offline the port is MockLlm, so nothing networks and the cost guard
trips on any real call in a non-live test.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from thesis_audiobook.context import Context
from thesis_audiobook.engine import map_structure_to_blocks, narrate_document
from thesis_audiobook.equations import equation_announcement
from thesis_audiobook.ir import Block, BlockType, Document
from thesis_audiobook.narrate import NARRATE_MAX_TOKENS, NARRATE_SYSTEM, NARRATE_VERSION
from thesis_audiobook.verifier import VERIFIER_VERSION
from thesis_audiobook.vision_structure import VisionStructureMap
from thesis_audiobook.warnings import LowConfidence


def _announce_nonprose(block: Block) -> str | None:
    """Deterministic, claim-safe announcement for a non-prose read block (bypasses the verifier).
    Equations are announced by their printed number (unnumbered -> None -> skipped); tables get a
    brief signpost; figure captions and the rest return None (skipped)."""
    if block.type is BlockType.equation_display:
        return equation_announcement(block.latex or block.text)
    if block.type is BlockType.table:
        return "A table is shown here."
    return None


class NarrateStage:
    name = "narrate"

    def run(self, doc: Document, ctx: Context) -> Document:
        if ctx.config.engine != "v2" or not doc.blocks:
            return doc
        structure = ctx.vision_structure or VisionStructureMap()
        assignments = map_structure_to_blocks(doc.blocks, structure)
        outcome = narrate_document(
            doc.blocks,
            assignments,
            generate=lambda prompt: self._generate(ctx, prompt),
            announce=_announce_nonprose,
            vision_for=self._vision_for(ctx),
            max_workers=ctx.config.narrate_workers,
        )
        ctx.narration = outcome
        for flag in outcome.flagged:
            ctx.warnings.add(
                LowConfidence(block_id=flag.block_id, reason=f"narration {flag.reason}", score=0.3)
            )
        ctx.log.info(
            "narrated",
            narrated=outcome.narrated,
            escalated=outcome.escalated,
            held=outcome.held,
            skipped=outcome.skipped,
            reviewed=outcome.reviewed,
        )
        return doc

    def _generate(self, ctx: Context, prompt: str) -> str:
        payload = f"{NARRATE_VERSION}\n{VERIFIER_VERSION}\n{type(ctx.llm).__name__}\n{prompt}"
        key = "narrate." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return cached.decode("utf-8")
        reply = ctx.llm.complete(prompt, system=NARRATE_SYSTEM, max_tokens=NARRATE_MAX_TOKENS)
        ctx.cache.put(key, reply.encode("utf-8"))
        return reply

    def _vision_for(self, ctx: Context) -> Callable[[Block], Callable[[str], str] | None]:
        """A per-block vision narrator over the block's rendered PAGE IMAGE, for held-segment
        escalation. Returns None when the page is unavailable (no escalation). Each call is
        content-addressed cached, and only invoked by the generator when the text path failed."""

        def vision_for(block: Block) -> Callable[[str], str] | None:
            if block.page is None or not ctx.page_images:
                return None
            index = block.page - 1
            if not 0 <= index < len(ctx.page_images):
                return None
            image = ctx.page_images[index]

            def generate(prompt: str) -> str:
                payload = (
                    f"{NARRATE_VERSION}\n{VERIFIER_VERSION}\nvision\n"
                    f"{type(ctx.vision).__name__}\n{block.page}\n{prompt}"
                )
                key = "narrate_vision." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
                cached = ctx.cache.get(key)
                if cached is not None:
                    return cached.decode("utf-8")
                reply = ctx.vision.describe(
                    prompt, [image], system=NARRATE_SYSTEM, max_tokens=NARRATE_MAX_TOKENS
                )
                ctx.cache.put(key, reply.encode("utf-8"))
                return reply

            return generate

        return vision_for
