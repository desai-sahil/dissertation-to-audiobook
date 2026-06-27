"""Phase 4: a final LLM red-flag check of the narration SCRIPT before any TTS spend.

Unlike the extraction QC (which audits the raw markdown), this reads the FINISHED script -
after glossing, citation resolution, normalization, abbreviation expansion - so it catches
TRANSFORM defects that only appear in what will actually be narrated: raw LaTeX/markup that
leaked, a nonsensical equation gloss, a citation that reads wrong, an abbreviation never
expanded, text cut off mid-sentence. It is read-only (it flags, never rewrites - claim-safety),
the deterministic no-leak invariant still guarantees the mechanical cases, and this is the
judgment layer on top. The CLI stops before ElevenLabs when there is a HIGH-severity flag.
This module is pure; the cached LLM call lives in stages/script_qc.py.
"""

from __future__ import annotations

import json
import re
from typing import Any

from thesis_audiobook.extraction_qc import ExtractionIssue
from thesis_audiobook.ir import StrictModel

SCRIPT_QC_VERSION = "scriptqc-v1"
SCRIPT_QC_SYSTEM = (
    "You are the final proofreader of an AUDIOBOOK NARRATION SCRIPT generated from a thesis. "
    "Flag ONLY things that would sound wrong or broken when read aloud. Do NOT rewrite the "
    "text or comment on the science/writing. Return ONLY the requested JSON; no prose, no fences."
)
SCRIPT_QC_MAX_TOKENS = 16_384


class ScriptQcReport(StrictModel):
    summary: str = ""
    issues: list[ExtractionIssue] = []

    def is_empty(self) -> bool:
        return not self.issues and not self.summary.strip()

    def high_severity(self) -> list[ExtractionIssue]:
        return [issue for issue in self.issues if issue.severity == "high"]


def build_script_qc_prompt(script: str) -> str:
    return (
        "Below is the FINAL narration script for an audiobook (already converted from a PhD "
        "thesis - equations glossed, citations resolved, abbreviations expanded). Audit it for "
        "RED FLAGS that would sound wrong when read aloud, and rate each by severity.\n\n"
        "Look for: raw LaTeX or math markup that leaked ('$', '\\frac', '<sup>', '_{'); a "
        "garbled or nonsensical equation gloss; a citation that reads wrong (a dangling 'as "
        "shown in', 'and others' with no name, a stray bracket); an abbreviation never "
        "expanded or expanded twice; a sentence cut off mid-thought; obvious OCR garble; a "
        "symbol that will be mispronounced. Severity HIGH = corrupts meaning or is clearly "
        "broken (raw LaTeX, garbled gloss, wrong number); medium/low = awkward but "
        "understandable. Do NOT flag normal prose or stylistic choices.\n\n"
        "Return ONLY this JSON:\n"
        '{"summary":"one-paragraph readiness assessment","issues":[{"kind":"raw_latex|'
        'broken_gloss|citation_error|abbrev_error|truncation|ocr_garble|mispronunciation|other"'
        ',"severity":"high|medium|low","location":"a short verbatim quote from the script",'
        '"detail":"what is wrong","suggestion":"how to fix"}]}\n'
        "If the script is clean, return an empty issues list with a summary saying it is ready.\n\n"
        "=== SCRIPT ===\n"
        f"{script}\n"
    )


def parse_script_qc(raw: str) -> ScriptQcReport:
    """Parse the model's JSON; an empty report on any failure (offline mock -> no flags)."""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return ScriptQcReport()
    try:
        data: Any = json.loads(text[start : end + 1])
        return ScriptQcReport.model_validate(data)
    except Exception:
        return ScriptQcReport()


def render_script_qc_md(report: ScriptQcReport) -> str:
    lines = ["# Pre-TTS script QC (phase 4)", ""]
    if report.is_empty():
        lines.append("No red flags reported (offline mock, or the script is clean).")
        return "\n".join(lines) + "\n"

    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    if report.summary.strip():
        lines += ["## Summary", "", report.summary.strip(), ""]
    order = {"high": 0, "medium": 1, "low": 2}
    issues = sorted(report.issues, key=lambda i: order.get(i.severity, 3))
    high = len(report.high_severity())
    lines += [
        f"## Red flags ({len(issues)} total, {high} high-severity)",
        "",
        "| Severity | Kind | Location | Detail | Suggestion |",
        "|---|---|---|---|---|",
    ]
    for i in issues:
        lines.append(
            f"| {cell(i.severity)} | {cell(i.kind)} | {cell(i.location)} "
            f"| {cell(i.detail)} | {cell(i.suggestion)} |"
        )
    return "\n".join(lines) + "\n"
