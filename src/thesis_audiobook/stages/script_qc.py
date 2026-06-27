"""Stage: phase-4 pre-TTS script QC.

Runs after assemble_script (the script is ready) and before lexicon/tts (the first ElevenLabs
spend). One cached LLM call audits the finished narration script for red flags; the report
lands on ctx.script_qc_report and the CLI gates on it. Read-only (never edits the script);
mock LLM -> empty report -> no-op offline; gated by config.script_qc. No I/O here.
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document
from thesis_audiobook.script_qc import (
    SCRIPT_QC_MAX_TOKENS,
    SCRIPT_QC_SYSTEM,
    SCRIPT_QC_VERSION,
    ScriptQcReport,
    build_script_qc_prompt,
    parse_script_qc,
)


class ScriptQcStage:
    name = "script_qc"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.script_qc or not (doc.script or "").strip():
            return doc
        report = self._audit(doc.script or "", ctx)
        ctx.script_qc_report = report
        if not report.is_empty():
            ctx.log.info("script_qc", issues=len(report.issues), high=len(report.high_severity()))
        return doc

    def _audit(self, script: str, ctx: Context) -> ScriptQcReport:
        payload = f"{SCRIPT_QC_VERSION}\n{type(ctx.llm).__name__}\n{script}"
        key = "scriptqc." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_script_qc(cached.decode("utf-8"))
        report = parse_script_qc(
            ctx.llm.complete(
                build_script_qc_prompt(script),
                system=SCRIPT_QC_SYSTEM,
                max_tokens=SCRIPT_QC_MAX_TOKENS,
            )
        )
        if not report.is_empty():
            ctx.cache.put(key, report.model_dump_json().encode("utf-8"))
        return report
