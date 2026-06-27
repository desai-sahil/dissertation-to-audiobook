"""Stage: the guarded, verified auto-repair LOOP (runs before the phase-4 QC gate).

A generator-verifier loop. Each round: the writer (one cached LLM call) proposes find/replace
fixes for the current script; candidate_repairs keeps only those that pass the deterministic
no-fabrication guard and whose anchor is verbatim in the script; then an independent AUDITOR PANEL
(two adversarial LLM calls per edit, both must pass, fail-closed) checks each survivor against its
anchor; the verified edits are applied to the chunk texts (so block_ids - and provenance - are
preserved) and doc.script is re-derived. The loop re-reads the repaired script and repeats until a
round verifies nothing (convergence) or a small iteration cap. The phase-4 script QC then audits
the result and gates on it.

Two safety layers under every applied edit - the deterministic guard (numbers/years/names) and the
auditor panel (semantic claim/relation changes the guard cannot see). Every call is cached, so the
loop is deterministic and cheap to re-run; the offline mock proposes nothing -> the loop is a
no-op. No I/O here (the cache is a port). Gated by config.script_repair.
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.faithfulness import (
    AUDIT_FRAMINGS,
    AUDITOR_MAX_TOKENS,
    AUDITOR_SYSTEM,
    AUDITOR_VERSION,
    AuditVerdict,
    build_audit_prompt,
    panel_faithful,
    parse_audit_verdict,
)
from thesis_audiobook.ir import Document
from thesis_audiobook.script_repair import (
    SCRIPT_REPAIR_MAX_TOKENS,
    SCRIPT_REPAIR_SYSTEM,
    SCRIPT_REPAIR_VERSION,
    AppliedRepair,
    RejectedRepair,
    ScriptRepair,
    ScriptRepairPlan,
    apply_one,
    build_script_repair_prompt,
    candidate_repairs,
    parse_script_repair_plan,
)

_MAX_ITERS = 3  # backstop; the loop normally stops earlier when a round verifies nothing


class ScriptRepairStage:
    name = "script_repair"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.script_repair or not (doc.script or "").strip():
            return doc
        applied: list[AppliedRepair] = []
        rejected: list[RejectedRepair] = []
        first_plan: ScriptRepairPlan | None = None
        for _ in range(_MAX_ITERS):
            plan = self._plan(doc.script or "", ctx)
            if first_plan is None:
                first_plan = plan
            candidates, guard_rejected = candidate_repairs(doc.script or "", plan.repairs)
            rejected.extend(guard_rejected)
            verified = [edit for edit in candidates if self._verified(edit, ctx, rejected)]
            if not verified:
                break  # converged: nothing left that is both safe and verified
            for edit in verified:
                count = apply_one(doc.chunks, edit)
                applied.append(
                    AppliedRepair(
                        find=edit.find, replace=edit.replace, count=count, reason=edit.reason
                    )
                )
            doc.script = "".join(chunk.text for chunk in doc.chunks)
        ctx.script_repair_plan = first_plan
        ctx.script_repair_applied = applied
        ctx.script_repair_rejected = rejected
        if applied or rejected:
            ctx.log.info("script_repair", applied=len(applied), rejected=len(rejected))
        return doc

    def _verified(self, edit: ScriptRepair, ctx: Context, rejected: list[RejectedRepair]) -> bool:
        """Run the full auditor panel on one edit; record a rejection if it fails (fail-closed)."""
        verdicts = [
            self._audit(edit.find, edit.replace, key, framing, ctx)
            for key, framing in AUDIT_FRAMINGS
        ]
        if panel_faithful(verdicts):
            return True
        why = next((v.reason for v in verdicts if not v.faithful), "rejected")
        rejected.append(RejectedRepair(find=edit.find, replace=edit.replace, why=f"auditor: {why}"))
        return False

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

    def _audit(
        self, anchor: str, output: str, lens: str, framing: str, ctx: Context
    ) -> AuditVerdict:
        payload = f"{AUDITOR_VERSION}\n{type(ctx.llm).__name__}\n{lens}\n{anchor}\n=>\n{output}"
        key = "audit." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return AuditVerdict.model_validate_json(cached)
        verdict = parse_audit_verdict(
            ctx.llm.complete(
                build_audit_prompt(anchor, output, framing),
                system=AUDITOR_SYSTEM,
                max_tokens=AUDITOR_MAX_TOKENS,
            )
        )
        ctx.cache.put(key, verdict.model_dump_json().encode("utf-8"))
        return verdict
