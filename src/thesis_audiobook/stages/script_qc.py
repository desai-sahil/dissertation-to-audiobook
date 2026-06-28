"""Stage: phase-4 pre-TTS script QC, as a BOUNDED agentic loop.

Runs after assemble_script and before lexicon/tts (the first ElevenLabs spend). Capped at one fix:
  1. AUDIT (ctx.llm, e.g. Sonnet) - find red flags in the finished script.
  2. If flags remain and config.qc_loop: ONE FIX pass (ctx.llm) turns the flags into safe
     find/replace edits (reusing the script-repair apply: whole-token, minimal-edit, tidy).
  3. CONFIRM (ctx.verifier_llm, Opus by default) - re-audit the fixed script ONCE.
  4. Drop out. The final report (confirm if it ran, else the audit) lands on ctx.script_qc_report;
     the CLI gates the billed render on its high-severity flags.

Cost is bounded: a clean script costs one audit call; a defective one costs audit + fix + one Opus
confirm, no further iteration. Valid reports (even clean ones) are cached so re-runs do not re-bill.
Mock LLM -> empty audit -> loop never fires -> no-op offline. Read-only when qc_loop is off. Gated
by config.script_qc. No I/O here.
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.extraction_qc import ExtractionIssue
from thesis_audiobook.ir import Document
from thesis_audiobook.ports.llm import LlmClient
from thesis_audiobook.qc_fix import QC_FIX_SYSTEM, QC_FIX_VERSION, build_qc_fix_prompt
from thesis_audiobook.script_qc import (
    SCRIPT_QC_MAX_TOKENS,
    SCRIPT_QC_SYSTEM,
    SCRIPT_QC_VERSION,
    ScriptQcReport,
    build_script_qc_prompt,
    is_qc_response,
    keep_locatable,
    parse_script_qc,
)
from thesis_audiobook.script_repair import (
    SCRIPT_REPAIR_MAX_TOKENS,
    AppliedRepair,
    apply_one,
    candidate_repairs,
    parse_script_repair_plan,
)
from thesis_audiobook.stages.script_repair import tidy_punctuation


class ScriptQcStage:
    name = "script_qc"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.script_qc or not (doc.script or "").strip():
            return doc
        # The SWEEP (audit) uses the thorough model (Opus) when the loop is on - it found defects
        # the cheap model missed; read-only mode (--no-qc-loop) audits cheaply on the pipeline LLM.
        audit_llm = ctx.verifier_llm if ctx.config.qc_loop else ctx.llm
        ctx.status.update("QC audit (Opus)" if ctx.config.qc_loop else "QC audit")
        report = self._audit(doc.script or "", audit_llm, ctx, phase="audit")
        if ctx.config.qc_loop and report.issues:
            ctx.status.update("QC fix (Sonnet)")
            applied = self._fix(doc, report.issues, ctx)  # the FIX is on the cheap model (Sonnet)
            if applied:
                doc.script = "".join(chunk.text for chunk in doc.chunks)
                ctx.script_repair_applied = [*ctx.script_repair_applied, *applied]
                # CONFIRM once on the thorough model - the second and final Opus sweep.
                ctx.status.update("QC confirm (Opus)")
                report = self._audit(doc.script or "", ctx.verifier_llm, ctx, phase="confirm")
                ctx.log.info("qc_loop", fixed=len(applied), remaining=len(report.issues))
        ctx.script_qc_report = report
        if not report.is_empty():
            ctx.log.info("script_qc", issues=len(report.issues), high=len(report.high_severity()))
        return doc

    def _audit(self, script: str, llm: LlmClient, ctx: Context, *, phase: str) -> ScriptQcReport:
        payload = f"{SCRIPT_QC_VERSION}\n{phase}\n{type(llm).__name__}\n{script}"
        key = "scriptqc." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_script_qc(cached.decode("utf-8"))
        raw = llm.complete(
            build_script_qc_prompt(script), system=SCRIPT_QC_SYSTEM, max_tokens=SCRIPT_QC_MAX_TOKENS
        )
        # Honesty filter: drop flags whose location is not a verbatim substring of the script (the
        # model paraphrased or hallucinated it). They cannot be fixed and must not block the gate.
        report = keep_locatable(parse_script_qc(raw), script)
        if is_qc_response(
            raw
        ):  # cache a well-formed report (even a clean one); skip offline garbage
            ctx.cache.put(key, report.model_dump_json().encode("utf-8"))
        return report

    def _fix(
        self, doc: Document, issues: list[ExtractionIssue], ctx: Context
    ) -> list[AppliedRepair]:
        """One cached fix pass: turn the flags into safe edits, applied whole-token then tidied."""
        script = doc.script or ""
        flag_keys = "\n".join(f"{i.kind}:{i.location}" for i in issues)
        payload = f"{QC_FIX_VERSION}\n{type(ctx.llm).__name__}\n{script}\n{flag_keys}"
        key = "qcfix." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            plan = parse_script_repair_plan(cached.decode("utf-8"))
        else:
            raw = ctx.llm.complete(
                build_qc_fix_prompt(script, issues),
                system=QC_FIX_SYSTEM,
                max_tokens=SCRIPT_REPAIR_MAX_TOKENS,
            )
            plan = parse_script_repair_plan(raw)
            if not plan.is_empty():
                ctx.cache.put(key, raw.encode("utf-8"))
        candidates, _ = candidate_repairs(script, plan.repairs)
        applied: list[AppliedRepair] = []
        for edit in candidates:
            count = apply_one(doc.chunks, edit)
            if count:
                applied.append(
                    AppliedRepair(
                        find=edit.find, replace=edit.replace, count=count, reason=edit.reason
                    )
                )
        if applied:
            for chunk in doc.chunks:
                chunk.text = tidy_punctuation(chunk.text)
        return applied
