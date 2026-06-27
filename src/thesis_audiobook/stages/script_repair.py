"""Stage: guarded auto-repair of the narration script (runs before the phase-4 QC gate).

After assemble_script, one cached LLM call proposes find/replace pronunciation fixes; only the
ones passing the no-fabrication guard are applied, in place, to the chunk texts (so block_ids -
and therefore provenance - are preserved). doc.script is re-derived from the repaired chunks, so
the phase-4 script QC that runs next audits the post-repair script and the gate reflects it.

Read-only on content (the guard forbids fabricating numbers/years/names); mock LLM -> empty plan
-> no-op offline; gated by config.script_repair. No I/O here (the cache is a port).
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document
from thesis_audiobook.script_repair import (
    SCRIPT_REPAIR_MAX_TOKENS,
    SCRIPT_REPAIR_SYSTEM,
    SCRIPT_REPAIR_VERSION,
    ScriptRepairPlan,
    apply_script_repairs,
    build_script_repair_prompt,
    parse_script_repair_plan,
)


class ScriptRepairStage:
    name = "script_repair"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.script_repair or not (doc.script or "").strip():
            return doc
        plan = self._plan(doc.script or "", ctx)
        applied, rejected = apply_script_repairs(doc.chunks, plan.repairs)
        if applied:
            doc.script = "".join(chunk.text for chunk in doc.chunks)
        ctx.script_repair_plan = plan
        ctx.script_repair_applied = applied
        ctx.script_repair_rejected = rejected
        if applied or rejected:
            ctx.log.info("script_repair", applied=len(applied), rejected=len(rejected))
        return doc

    def _plan(self, script: str, ctx: Context) -> ScriptRepairPlan:
        payload = f"{SCRIPT_REPAIR_VERSION}\n{type(ctx.llm).__name__}\n{script}"
        key = "scriptrepair." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_script_repair_plan(cached.decode("utf-8"))
        plan = parse_script_repair_plan(
            ctx.llm.complete(
                build_script_repair_prompt(script),
                system=SCRIPT_REPAIR_SYSTEM,
                max_tokens=SCRIPT_REPAIR_MAX_TOKENS,
            )
        )
        if not plan.is_empty():
            ctx.cache.put(key, plan.model_dump_json().encode("utf-8"))
        return plan
