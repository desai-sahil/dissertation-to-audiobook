"""Stage: the LLM script-repair loop (runs before the phase-4 QC gate).

Each round: the writer (one cached LLM call) proposes find/replace edits that fix how NOTATION is
spoken; candidate_repairs keeps the ones that are a verbatim substring of the script; each is
applied on whole-token matches (apply_one), and doc.script is re-derived. The loop re-reads the
repaired script and repeats until a round changes nothing (convergence) or a small iteration cap.

The model is TRUSTED within its narrow scope (vocalizing notation, never the author's spelling /
grammar / names) - there is no auditor or no-fabrication guard; the ledger records every applied
and unapplied edit so a human can review. Every call is cached, so the loop is deterministic and
cheap to re-run; the offline mock proposes nothing -> the loop is a no-op. No I/O here (the cache
is a port). Gated by config.script_repair.
"""

from __future__ import annotations

import hashlib
import re

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document
from thesis_audiobook.script_repair import (
    SCRIPT_COPYEDIT_SYSTEM,
    SCRIPT_REPAIR_MAX_TOKENS,
    SCRIPT_REPAIR_SYSTEM,
    SCRIPT_REPAIR_VERSION,
    AppliedRepair,
    RejectedRepair,
    ScriptRepairPlan,
    apply_one,
    build_script_repair_prompt,
    candidate_repairs,
    parse_script_repair_plan,
)

_MAX_ITERS = 3  # backstop; the loop normally stops earlier when a round changes nothing
_DOUBLED_COMMA = re.compile(r"\s*,(?:\s*,)+")


def tidy_punctuation(text: str) -> str:
    """Safety net: collapse doubled commas (",," / ", ,") and tidy empty parenthetical edges that
    a too-aggressive edit may leave behind. Idempotent and a no-op on clean text."""
    text = _DOUBLED_COMMA.sub(", ", text)  # ",," / ", ," -> ", "
    text = re.sub(r"\(\s*,\s*", "(", text)  # "( ," -> "("
    text = re.sub(r"\s*,\s*\)", ")", text)  # ", )" -> ")"
    return re.sub(r"[ \t]{2,}", " ", text)


class ScriptRepairStage:
    name = "script_repair"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.script_repair or not (doc.script or "").strip():
            return doc
        applied: list[AppliedRepair] = []
        rejected: list[RejectedRepair] = []
        first_plan: ScriptRepairPlan | None = None
        for round_num in range(1, _MAX_ITERS + 1):
            ctx.status.update(f"Script repair round {round_num}/{_MAX_ITERS}")
            plan = self._plan(doc.script or "", ctx)
            if first_plan is None:
                first_plan = plan
            candidates, not_applicable = candidate_repairs(
                doc.script or "", plan.repairs, copyedit=ctx.config.copyedit
            )
            rejected.extend(not_applicable)
            changed = False
            for edit in candidates:
                count = apply_one(doc.chunks, edit)
                if count:
                    applied.append(
                        AppliedRepair(
                            find=edit.find,
                            replace=edit.replace,
                            count=count,
                            reason=edit.reason,
                            kind=edit.kind,
                        )
                    )
                    changed = True
            if not changed:
                break  # converged: nothing left to apply
            doc.script = "".join(chunk.text for chunk in doc.chunks)
        # Safety net: tidy any doubled punctuation an edit may have left (provenance preserved -
        # we only rewrite chunk.text in place).
        for chunk in doc.chunks:
            chunk.text = tidy_punctuation(chunk.text)
        doc.script = "".join(chunk.text for chunk in doc.chunks)
        ctx.script_repair_plan = first_plan
        ctx.script_repair_applied = applied
        ctx.script_repair_rejected = rejected
        if applied or rejected:
            ctx.log.info("script_repair", applied=len(applied), rejected=len(rejected))
        return doc

    def _plan(self, script: str, ctx: Context) -> ScriptRepairPlan:
        copyedit = ctx.config.copyedit
        mode = "copyedit" if copyedit else "as-written"
        payload = f"{SCRIPT_REPAIR_VERSION}\n{mode}\n{type(ctx.llm).__name__}\n{script}"
        key = "scriptrepair." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_script_repair_plan(cached.decode("utf-8"))
        system = SCRIPT_COPYEDIT_SYSTEM if copyedit else SCRIPT_REPAIR_SYSTEM
        plan = parse_script_repair_plan(
            ctx.llm.complete(
                build_script_repair_prompt(script, copyedit=copyedit),
                system=system,
                max_tokens=SCRIPT_REPAIR_MAX_TOKENS,
            )
        )
        if not plan.is_empty():
            ctx.cache.put(key, plan.model_dump_json().encode("utf-8"))
        return plan
