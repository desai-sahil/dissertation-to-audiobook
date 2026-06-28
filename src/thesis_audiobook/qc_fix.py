"""QC-driven fix: turn the phase-4 QC's red flags into safe find/replace edits. Pure (prompt only).

The QC audit flags pipeline defects and suggests fixes; this builds a prompt asking the model to
RESOLVE those specific flags with minimal find/replace edits - the same {"repairs":[...]} shape as
the script-repair writer, so the existing safe apply (candidate_repairs / apply_one whole-token /
_tidy_punctuation) and parser (parse_script_repair_plan) are reused unchanged. The model call and
the cache live in the stage.
"""

from __future__ import annotations

from thesis_audiobook.extraction_qc import ExtractionIssue

QC_FIX_VERSION = "qcfix-v1"
QC_FIX_SYSTEM = (
    "You repair an AUDIOBOOK NARRATION SCRIPT by resolving ONLY the specific red flags listed. "
    "Propose minimal find/replace edits: each `replace` must be its `find` with ONLY the flagged "
    "problem fixed - keep every other character (punctuation, parentheses, spacing) exactly as in "
    "`find`. Do NOT fix the author's spelling, grammar, or names; do NOT add a number, year, or "
    "citation; do NOT restructure sentences. If a flag cannot be fixed safely, skip it. Return "
    "ONLY the requested JSON; no prose, no markdown fences."
)


def _flag_line(issue: ExtractionIssue) -> str:
    return f'- [{issue.severity}/{issue.kind}] "{issue.location}" :: {issue.detail}' + (
        f" (suggestion: {issue.suggestion})" if issue.suggestion else ""
    )


def build_qc_fix_prompt(script: str, issues: list[ExtractionIssue]) -> str:
    flags = "\n".join(_flag_line(i) for i in issues)
    return (
        "Below is an audiobook narration script and a list of RED FLAGS to fix. For each flag, "
        "give ONE find/replace edit that resolves it. 'find' MUST be an exact substring of the "
        "script (copy it verbatim, with enough context to be unambiguous), short and localized.\n\n"
        "RED FLAGS:\n"
        f"{flags}\n\n"
        'Return ONLY this JSON: {"repairs":[{"find":"exact substring","replace":"the fix",'
        '"reason":"which flag"}]}\n\n'
        "=== SCRIPT ===\n"
        f"{script}\n"
    )
