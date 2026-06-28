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
        )
        ctx.narration = outcome
        for flag in outcome.flagged:
            ctx.warnings.add(
                LowConfidence(block_id=flag.block_id, reason=f"narration {flag.reason}", score=0.3)
            )
        ctx.log.info(
            "narrated",
            narrated=outcome.narrated,
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
