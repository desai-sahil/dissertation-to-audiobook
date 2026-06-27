"""Stage: the Structurer (LLM block-kind classifier), runs after build_ir, before the cartographer.

One cached LLM call labels each block's kind; apply_structure sets block.type from the labels and
returns a change log. The cartographer (regions) and select (keep/skip) then run on the corrected
types, so e.g. a code listing the regex missed is typed `code` and skipped. Claim-safe (only types
change, never text), and every change is recorded on ctx + emitted as a Gate-A warning so nothing
is reclassified silently. Cached -> deterministic; offline mock -> empty plan -> no-op. Gated by
config.structurer. No I/O here (the cache is a port).
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, Document
from thesis_audiobook.structurer import (
    STRUCTURER_MAX_TOKENS,
    STRUCTURER_SYSTEM,
    STRUCTURER_VERSION,
    StructurePlan,
    apply_structure,
    build_outline,
    build_structurer_prompt,
    parse_structure_plan,
    suspicious_blocks,
)
from thesis_audiobook.warnings import LowConfidence


class StructurerStage:
    name = "structurer"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.structurer or not doc.blocks:
            return doc
        # Triage first: only blocks the cheap pass may have mis-typed are sent to the model.
        # If nothing looks suspicious, there is no LLM call at all.
        suspects = suspicious_blocks(doc.blocks)
        if not suspects:
            return doc
        plan = self._plan(suspects, ctx)
        if plan.is_empty():
            # Suspects existed but the model returned nothing usable (e.g. a malformed JSON
            # response). Fail-soft leaves those blocks as prose, so surface it loudly rather
            # than silently narrate possible code; an uncached empty plan self-heals on re-run.
            ctx.warnings.add(
                LowConfidence(
                    block_id=suspects[0].id,
                    reason=(
                        f"structurer: {len(suspects)} suspicious block(s) but the model returned "
                        "no labels - possible code/non-prose left unskipped; re-run to retry"
                    ),
                    score=0.2,
                )
            )
            ctx.log.info("structurer_empty", suspects=len(suspects))
            return doc
        changes = apply_structure(doc.blocks, plan)
        ctx.reclassifications = changes
        for change in changes:
            ctx.warnings.add(
                LowConfidence(
                    block_id=change.id,
                    reason=f"structurer reclassified {change.from_type} -> {change.to_type}",
                    score=0.6,
                )
            )
        if changes:
            ctx.log.info("structurer", reclassified=len(changes))
        return doc

    def _plan(self, suspects: list[Block], ctx: Context) -> StructurePlan:
        outline = build_outline(suspects)
        payload = f"{STRUCTURER_VERSION}\n{type(ctx.llm).__name__}\n{outline}"
        key = "structurer." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_structure_plan(cached.decode("utf-8"))
        plan = parse_structure_plan(
            ctx.llm.complete(
                build_structurer_prompt(outline),
                system=STRUCTURER_SYSTEM,
                max_tokens=STRUCTURER_MAX_TOKENS,
            )
        )
        if not plan.is_empty():
            ctx.cache.put(key, plan.model_dump_json().encode("utf-8"))
        return plan
