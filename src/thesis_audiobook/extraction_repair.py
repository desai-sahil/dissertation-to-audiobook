"""Guarded, claim-safe repair of the extraction markdown (pure core).

The two-pass loop (orchestrated in the CLI): (1) the model proposes {broken -> fixed} edits
for TYPOGRAPHIC/OCR noise; we apply only the edits that pass a content-preservation guard,
deterministically, producing a cleaned markdown; (2) the model re-reads the cleaned markdown
and flags whatever remains, before it goes downstream.

The guard is the safety invariant: an edit is applied ONLY if it preserves the exact sequence
of word-tokens AND their case - i.e. tokens(broken) == tokens(fixed), where a token is an
NFC-normalized, case-preserved alphanumeric run. So an applied edit may change only the
NON-word characters between/around words (spaces, detached accents, stray marks, punctuation).
It can never change a word's letters or case, change a number, add/drop/merge/split a word, or
flip a claim. Rejected (sent to human review, never applied): "is not significant" -> "is
significant" (drops a word), "not able" -> "notable" (merge), "US" -> "us" (case), "re-cover"
-> "recover" (semantic hyphen), "5½" -> "512" (number). Accepted: "Scholander ¨" ->
"Scholander", "g  s" -> "g s". Word-splitting hyphenation ("me-asurable" -> "measurable") is
deliberately NOT done here - it's indistinguishable from a semantic hyphen without a dictionary,
so it's left to the curator (which guards genuine compounds with whole-document context). This
module is pure; the cached model calls + file writes live in the CLI.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from thesis_audiobook.extraction_qc import ExtractionIssue
from thesis_audiobook.ir import StrictModel

EXTRACTION_REPAIR_VERSION = "extrepair-v1"
EXTRACTION_REPAIR_SYSTEM = (
    "You repair PDF-to-markdown EXTRACTION NOISE in a scientific thesis. You may ONLY change "
    "the spaces, detached accents, stray marks, and punctuation BETWEEN or AROUND words. Keep "
    "every word and number exactly as written - same spelling, same CASE, same order. NEVER "
    "merge or split words, never change case, never rejoin a hyphenated line break, never touch "
    "a number. Return ONLY the requested JSON; no prose, no markdown fences."
)
EXTRACTION_REPAIR_MAX_TOKENS = 16_384
_MAX_SPAN = 400  # an edit longer than this is reported, not auto-applied (limits blast radius)


class RepairEdit(StrictModel):
    broken: str  # exact substring as it appears in the markdown
    fixed: str  # the same text with ONLY typographic noise removed
    reason: str = ""


class ExtractionRepairPlan(StrictModel):
    summary: str = ""
    repairs: list[RepairEdit] = []
    issues: list[ExtractionIssue] = []  # defects that need human review, not auto-fixable

    def is_empty(self) -> bool:
        return not self.repairs and not self.issues and not self.summary.strip()


class AppliedEdit(StrictModel):
    broken: str
    fixed: str
    count: int
    reason: str = ""


class RejectedEdit(StrictModel):
    broken: str
    fixed: str
    why: str


_WORD = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    """The sequence of NFC-normalized, CASE-PRESERVED alphanumeric word-tokens.

    Case, word boundaries, and a word's letters are all meaning-bearing when read aloud, so
    the guard preserves them; only the non-word characters between/around tokens may change.
    NFC (not NFKD) so a decomposed accent equals its precomposed form, while fractions ("½")
    and superscripts ("²") are NOT decomposed into digits - that would let a number change
    ("5½" -> "512") slip through.
    """
    return _WORD.findall(unicodedata.normalize("NFC", text))


def is_safe_repair(broken: str, fixed: str) -> bool:
    """True iff broken->fixed cannot change spoken content: it preserves the exact sequence of
    word-tokens AND their case, changing only non-word noise. Rejects case changes (US->us),
    word merge/split incl. hyphenation rejoin (not able->notable, re-cover->recover, me-asurable
    ->measurable - left to the dictionary-guarded curator), and any letter/number change."""
    if not broken or broken == fixed or len(broken) > _MAX_SPAN:
        return False
    broken_tokens = _tokens(broken)
    return broken_tokens != [] and broken_tokens == _tokens(fixed)


def apply_repairs(
    markdown: str, repairs: list[RepairEdit]
) -> tuple[str, list[AppliedEdit], list[RejectedEdit]]:
    """Apply only guard-passing, locatable edits (all occurrences), longest broken first so a
    shorter edit cannot partially clobber a longer one. Returns (cleaned, applied, rejected)."""
    cleaned = markdown
    applied: list[AppliedEdit] = []
    rejected: list[RejectedEdit] = []
    for edit in sorted(repairs, key=lambda e: len(e.broken), reverse=True):
        if not is_safe_repair(edit.broken, edit.fixed):
            rejected.append(
                RejectedEdit(
                    broken=edit.broken,
                    fixed=edit.fixed,
                    why="would change content (word tokens or case differ) or span too large",
                )
            )
            continue
        if edit.broken not in cleaned:
            rejected.append(
                RejectedEdit(broken=edit.broken, fixed=edit.fixed, why="not found in markdown")
            )
            continue
        count = cleaned.count(edit.broken)
        cleaned = cleaned.replace(edit.broken, edit.fixed)
        applied.append(
            AppliedEdit(broken=edit.broken, fixed=edit.fixed, count=count, reason=edit.reason)
        )
    return cleaned, applied, rejected


def build_repair_prompt(markdown: str) -> str:
    return (
        "Below is the full markdown a PDF parser (Marker) produced from a scientific PhD "
        "thesis. Propose edits that REMOVE TYPOGRAPHIC / OCR NOISE so it reads cleanly aloud, "
        "and separately flag defects you must NOT auto-fix.\n\n"
        "Safe to repair (put in 'repairs'): detached accents ('Scholander ¨' -> "
        "'Scholander'), stray combining marks, doubled/odd spacing ('g  s' -> 'g s'), and "
        "stray punctuation between words. RULE: 'fixed' MUST have the SAME words and numbers as "
        "'broken', in the same order, with the same spelling and CASE - you may only change the "
        "spaces/marks/punctuation between or around the words. NEVER merge or split words, "
        "never change case, never rejoin a hyphenated line break, never alter a number. 'broken' "
        "must be an EXACT substring of the markdown (copy it verbatim, a few words around the "
        "defect).\n\n"
        "NOT safe to auto-fix (put in 'issues', do not invent a 'fixed'): OCR letter "
        "substitutions, hyphenation splits ('me-asurable'), merged/split words, missing or "
        "truncated content, garbled tables, anything where the correct text is uncertain.\n\n"
        "Return ONLY this JSON:\n"
        '{"summary":"one-paragraph assessment","repairs":[{"broken":"exact noisy substring",'
        '"fixed":"same text, noise removed","reason":"what noise"}],'
        '"issues":[{"kind":"ocr_garble|dropped_content|bad_table|other","severity":"high|'
        'medium|low","location":"section + short quote","detail":"...","suggestion":"..."}]}\n\n'
        "=== MARKDOWN ===\n"
        f"{markdown}\n"
    )


def parse_repair_plan(raw: str) -> ExtractionRepairPlan:
    """Parse the model's JSON; an empty plan on any failure (so the offline mock is a no-op)."""
    text = raw
    for fence in ("```json", "```"):
        text = text.replace(fence, "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return ExtractionRepairPlan()
    try:
        data: Any = json.loads(text[start : end + 1])
        return ExtractionRepairPlan.model_validate(data)
    except Exception:
        return ExtractionRepairPlan()


def render_repair_report(
    plan: ExtractionRepairPlan,
    applied: list[AppliedEdit],
    rejected: list[RejectedEdit],
    verify_summary: str,
    verify_issues: list[ExtractionIssue],
) -> str:
    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = ["# Extraction repair report (two-pass, guarded)", ""]
    if plan.summary.strip():
        lines += ["## Pass 1 summary", "", plan.summary.strip(), ""]
    lines += [f"## Applied edits ({len(applied)})", ""]
    if applied:
        lines += ["| broken | fixed | times | reason |", "|---|---|---|---|"]
        lines += [
            f"| {cell(a.broken)} | {cell(a.fixed)} | {a.count} | {cell(a.reason)} |"
            for a in applied
        ]
    else:
        lines.append("None.")
    lines += ["", f"## Rejected edits ({len(rejected)}) - NOT applied (guard or not found)", ""]
    if rejected:
        lines += ["| broken | proposed fixed | why rejected |", "|---|---|---|"]
        lines += [f"| {cell(r.broken)} | {cell(r.fixed)} | {cell(r.why)} |" for r in rejected]
    else:
        lines.append("None.")
    if plan.issues:
        lines += ["", "## Flagged for human review (pass 1, not auto-fixable)", ""]
        lines += [
            f"- **{cell(i.severity)}/{cell(i.kind)}** {cell(i.location)}: {cell(i.detail)}"
            for i in plan.issues
        ]
    lines += ["", "## Pass 2 - residual issues on the CLEANED markdown", ""]
    if verify_summary.strip():
        lines += [verify_summary.strip(), ""]
    if verify_issues:
        lines += [
            f"- **{cell(i.severity)}/{cell(i.kind)}** {cell(i.location)}: {cell(i.detail)}"
            for i in verify_issues
        ]
    else:
        lines.append("No residual issues flagged.")
    return "\n".join(lines) + "\n"
