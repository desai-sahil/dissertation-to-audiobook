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
from typing import Any, cast

from thesis_audiobook.extraction_qc import ExtractionIssue
from thesis_audiobook.ir import StrictModel

SCRIPT_QC_VERSION = "scriptqc-v5"
SCRIPT_QC_SYSTEM = (
    "You are the final proofreader of an AUDIOBOOK NARRATION SCRIPT generated from a thesis. "
    "Flag ONLY defects the PIPELINE introduced or failed to render - never the author's own "
    "spelling, grammar, word choice, how a name is pronounced, or a number the author wrote (the "
    "audiobook reads the thesis as written). Note two INTENTIONAL behaviors that are CORRECT and "
    "must never be flagged: (1) in-text citations are deliberately discarded or genericized - the "
    "narration does NOT name authors or years, so a vague attribution ('researchers', 'several "
    "studies', 'prior work') or no citation at all is intended; (2) cross-reference "
    "numbers are read exactly as the author wrote them. Every 'location' you return MUST be an "
    "EXACT, VERBATIM substring copied from the script (never paraphrased, summarized, or "
    "reconstructed) so it can be located and fixed; if you cannot quote the problem verbatim, do "
    "not raise it. Do NOT rewrite the text or comment on the science/writing. Return ONLY the "
    "requested JSON; no prose, no fences."
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
        "thesis - equations announced by number, in-text citations intentionally discarded or "
        "genericized, abbreviations expanded). Audit it for RED FLAGS the PIPELINE got wrong, and "
        "rate each by severity.\n\n"
        "FLAG (pipeline defects): raw LaTeX or math markup that leaked ('$', '\\frac', '<sup>', "
        "'_{'); code or raw notation read aloud; a word mangled by extraction so it is no longer a "
        "real word (letters fused like 'comillimeters', or spaced-out characters 'C o e f f'); a "
        "wrong or malformed equation announcement; a citation marker the pipeline FAILED to remove "
        "(a leaked '[', a reference number read aloud as a number, a dangling 'as shown in.'); "
        "an abbreviation never expanded or expanded twice; a sentence cut mid-thought; a number "
        "or symbol voiced wrong.\n\n"
        "DO NOT FLAG (these are the AUTHOR's, or INTENDED behavior, not pipeline bugs): a plain "
        "misspelling of an otherwise-real word ('responce', 'stomotal'); grammar or awkward "
        "phrasing; the pronunciation of an ordinary word or a proper name; a GENERICIZED or absent "
        "citation ('researchers', 'several studies', 'prior work', or a sentence that names no "
        "source) - this is the intended narration; a cross-reference number read as the author "
        "wrote it (e.g. a wrong 'Section two point twenty-four' from the author's typo).\n\n"
        "Severity HIGH = a pipeline failure that corrupts meaning or is clearly broken (leaked "
        "LaTeX, code/garble read aloud, wrong number); medium/low = awkward but understandable.\n\n"
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


# Fold the cosmetic variants a model introduces when quoting a location, so a REAL flag is not
# dropped (and the render gate not silently passed) over a trivial difference - review-found: a
# trailing period, smart quotes, en/em dashes, ellipsis, zero-width chars, case, and re-spaced
# fusions all caused false drops. Errs toward KEEPING, so the gate blocks conservatively.
_CANON = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",  # curly single quotes
    "\u201c": '"', "\u201d": '"', "\u2032": "'", "\u2033": '"',  # curly double quotes / primes
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2026": ".",  # en/em dash, minus, ellipsis
    "\u00a0": " ", "\u200b": "", "\ufeff": "", "\u00ad": "",  # nbsp, zero-width, bom, soft hyphen
})  # fmt: skip
_EDGE = " \t\r\n.,;:!?\"'()[]{}"


def _canon(text: str) -> str:
    return " ".join(text.translate(_CANON).split()).casefold()


def found_verbatim(location: str, script: str) -> bool:
    """True if `location` locates in the script under whitespace/case/punctuation folding, with a
    whitespace-stripped fallback for re-spaced fusions. A flag that still does not locate was
    paraphrased or hallucinated (it cannot be fixed), so the loop drops it rather than chase a
    phantom; a defect quoted with only cosmetic drift is KEPT so it still blocks the gate."""
    loc = _canon(location).strip(_EDGE)
    if not loc:
        return False
    body = _canon(script)
    return loc in body or loc.replace(" ", "") in body.replace(" ", "")


def keep_locatable(report: ScriptQcReport, script: str) -> ScriptQcReport:
    """Drop issues whose location is not locatable in the script (honesty filter). A drop is noted
    in the summary, so the QC artifact never asserts a defect above an empty table (per rule 9)."""
    kept = [issue for issue in report.issues if found_verbatim(issue.location, script)]
    dropped = len(report.issues) - len(kept)
    summary = report.summary
    if dropped:
        summary = f"{summary} ({dropped} flagged item(s) dropped as unlocatable in the script.)"
        summary = summary.strip()
    return ScriptQcReport(summary=summary, issues=kept)


def is_qc_response(raw: str) -> bool:
    """True if `raw` is a well-formed QC report (a JSON object with an 'issues' list). A clean
    report (empty issues) is worth caching so re-runs do not re-bill; an offline/garbled response
    is not (so it is re-checked next run)."""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return False
    try:
        data: Any = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return False
    return isinstance(data, dict) and isinstance(cast("dict[str, Any]", data).get("issues"), list)


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
