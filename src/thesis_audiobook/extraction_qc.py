"""LLM oversight of the PDF->markdown extraction (pure prompt/parse/render).

A QC pass that has the model read the Marker markdown and flag EXTRACTION defects - OCR
garble, broken or dropped equations, merged/truncated blocks, missing or out-of-order
sections, mangled tables/figures - so they can be fixed (e.g. re-extracting those pages)
BEFORE the document goes downstream. Claim-safe: the model only REPORTS problems with short
verbatim anchors; it never rewrites the content. The cached LLM call and the file writes
live in the CLI composition root; this module is pure (prompt, parse, render).
"""

from __future__ import annotations

import json
import re
from typing import Any

from thesis_audiobook.ir import StrictModel

EXTRACTION_QC_VERSION = "extqc-v1"
EXTRACTION_QC_SYSTEM = (
    "You are a meticulous proofreader auditing a PDF-to-markdown extraction of a scientific "
    "thesis for EXTRACTION DEFECTS ONLY (not the author's writing quality). Return ONLY the "
    "requested JSON object - no prose, no markdown fences. Use short verbatim snippets as "
    "anchors; never rewrite or correct the text yourself."
)
# A defect report over a long thesis can be sizeable; output is billed per actual token.
EXTRACTION_QC_MAX_TOKENS = 16_384

_KINDS = (
    "ocr_garble, broken_equation, dropped_content, merged_blocks, truncation, "
    "missing_or_misordered_section, bad_table, bad_figure, heading_mislevel, other"
)


class ExtractionIssue(StrictModel):
    kind: str  # one of the _KINDS above
    severity: str  # high | medium | low
    location: str  # nearest heading/section + a short VERBATIM quote anchoring the spot
    detail: str  # what looks wrong
    suggestion: str  # e.g. "re-extract the pages around section 3.2"


class ExtractionQCReport(StrictModel):
    issues: list[ExtractionIssue] = []
    summary: str = ""

    def is_empty(self) -> bool:
        return not self.issues and not self.summary.strip()


def build_qc_prompt(markdown: str) -> str:
    return (
        "Below is the full markdown a PDF parser (Marker) produced from a scientific PhD "
        "thesis. Audit it for EXTRACTION DEFECTS that would harm an audiobook made from it. "
        "Look for: OCR garble or mojibake; equations that were dropped, truncated, or turned "
        "into nonsense; content visibly cut off mid-sentence at a page break; two blocks "
        "wrongly merged (a heading fused into body, or two paragraphs joined); sections that "
        "appear missing or out of order (gaps in numbering); tables or figure captions that "
        "came out garbled; headings at the wrong level. Do NOT report on the author's writing "
        "style or science - only extraction fidelity.\n\n"
        "Return ONLY this JSON:\n"
        '{"summary":"one-paragraph overall assessment of extraction quality",'
        '"issues":[{"kind":"<one of: ' + _KINDS + '>","severity":"high|medium|low",'
        '"location":"nearest heading/section + a short verbatim quote","detail":"what is '
        'wrong","suggestion":"how to fix, e.g. re-extract pages around section X"}]}\n\n'
        "Report the most important issues first. If extraction is clean, return an empty "
        "issues list with a summary saying so.\n\n"
        "=== MARKDOWN ===\n"
        f"{markdown}\n"
    )


def parse_qc(raw: str) -> ExtractionQCReport:
    """Parse the model's JSON into a report; an empty report on any failure, so a non-JSON
    response (e.g. the offline mock) degrades to no findings rather than crashing."""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return ExtractionQCReport()
    try:
        data: Any = json.loads(text[start : end + 1])
        return ExtractionQCReport.model_validate(data)
    except Exception:
        return ExtractionQCReport()


def render_qc_md(report: ExtractionQCReport) -> str:
    lines = ["# Extraction QC (LLM oversight of the Marker extraction)", ""]
    if report.is_empty():
        lines.append("No extraction issues reported (offline mock, or nothing flagged).")
        return "\n".join(lines) + "\n"

    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    if report.summary.strip():
        lines += ["## Summary", "", report.summary.strip(), ""]
    order = {"high": 0, "medium": 1, "low": 2}
    issues = sorted(report.issues, key=lambda i: order.get(i.severity, 3))
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    lines += [
        f"## Issues ({len(issues)}: "
        + ", ".join(f"{counts[s]} {s}" for s in ("high", "medium", "low") if s in counts)
        + ")",
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
