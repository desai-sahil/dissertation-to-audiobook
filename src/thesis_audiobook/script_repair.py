"""LLM repair of the narration SCRIPT: fix how NOTATION is vocalized. Pure core, no I/O.

The model reads the finished script and proposes small {find -> replace} edits that fix how
existing text READS ALOUD - units and symbols spoken in full, leaked LaTeX/markup turned into
words, chemical formulas voiced as their name, number/ordinal spacing artifacts. The edits are
applied as written (the model is trusted within this narrow scope) and every one is recorded in
the ledger for human review.

SCOPE, by design (not a content filter): this only changes how NOTATION is voiced. It does NOT
correct the author's spelling, grammar, word choice, or the pronunciation of ordinary words and
names - those are the author's and the audiobook reads the thesis as written. Edits are applied
on WHOLE TOKENS only (word boundaries), so a unit fix like "mm" -> "millimeters" can never rewrite
the middle of a word ("committee"). The cached model call and file writes live in the stage/CLI.
"""

from __future__ import annotations

import json
import re
from typing import Any

from thesis_audiobook.copyedit import copyedit_guard
from thesis_audiobook.extraction_qc import ExtractionIssue
from thesis_audiobook.ir import Chunk, StrictModel

SCRIPT_REPAIR_VERSION = "scriptrepair-v5"
# Strict, faithful mode (--as-written): vocalize notation ONLY, never the author's text.
SCRIPT_REPAIR_SYSTEM = (
    "You fix how an AUDIOBOOK NARRATION SCRIPT VOCALIZES notation - nothing else. You turn "
    "symbols, math notation, units, chemical formulas, leaked markup, and abbreviations into the "
    "natural spoken words a narrator should say. You do NOT correct the author's spelling, "
    "grammar, word choice, or the pronunciation of ordinary words and names - those are the "
    "author's and must be read exactly as written. Make the MINIMAL edit: your `replace` must be "
    "your `find` with ONLY the notation token changed - keep every surrounding character "
    "(parentheses, commas, other punctuation, spacing, hyphenation) EXACTLY as in `find`. Never "
    "add or remove parentheses or commas, never restructure the sentence. Tag every edit "
    'kind "notation". Return ONLY the requested JSON; no prose, no markdown fences.'
)
# Copy-edit mode (--copyedit, the default): also fix the author's clear MECHANICAL errors and
# extraction artifacts so a listener is not tripped up, but never change a value or a claim.
SCRIPT_COPYEDIT_SYSTEM = (
    "You prepare an AUDIOBOOK NARRATION SCRIPT from a scientific thesis so it reads cleanly aloud. "
    "You make small find/replace edits, and you TAG each with its `kind`:\n"
    '- "notation": vocalize a symbol/unit/math/chemical formula/leaked markup into spoken words.\n'
    '- "spelling": fix a clearly misspelled word (a non-word) -> its intended real word.\n'
    '- "grammar": fix subject-verb agreement or a wrong tense, OR improve READABILITY by adding '
    "small function words (an article, or 'in' before a unit) or turning a stray unit-parenthesis "
    "into commas so a measurement reads as a clean spoken clause - e.g. 'R s megapascals seconds "
    "per kilogram )' -> 'R s, in megapascals seconds per kilogram,'. This is welcome (it adds only "
    "function words/punctuation); apply it confidently, do NOT call it 'style' or withdraw it.\n"
    '- "spacing": split fused words or fix missing/extra spacing.\n'
    '- "extraction_artifact": remove a PDF-extraction leak (stray operator, leaked tag) that is '
    "not the author's intent.\n"
    "HARD RULES (a violation is a serious error): NEVER change a number, value, sign, unit, or "
    "measurement; NEVER add or remove a negation or scope word (not, no, only, all, more, less); "
    "NEVER insert a claim or hedge (e.g. 'significant'); NEVER PARAPHRASE or swap a content word "
    "(readability adds only function words/punctuation, it never changes meaning). "
    "If you suspect a NUMBER, SIGN, UNIT, or FACTUAL error (e.g. a sign that reads wrong), do NOT "
    "edit it - put it in `issues` for human review. Return ONLY the requested JSON; no fences."
)
SCRIPT_REPAIR_MAX_TOKENS = 16_384
_MAX_SPAN = 200  # a find longer than this is skipped (an edit should be a short, localized span)
# Edit kinds whose `replace` must clear the deterministic copy-edit guard (the author's own text).
# "notation" keeps its trusted scope; "data" is flag-only and never auto-applied.
_GUARDED_KINDS = frozenset({"spelling", "grammar", "spacing", "extraction_artifact"})


class ScriptRepair(StrictModel):
    find: str  # exact substring of the script whose NOTATION reads wrong aloud
    replace: str  # the same content, with the notation voiced as spoken words
    reason: str = ""
    kind: str = "notation"  # notation | spelling | grammar | spacing | extraction_artifact | data


class ScriptRepairPlan(StrictModel):
    summary: str = ""
    repairs: list[ScriptRepair] = []
    issues: list[ExtractionIssue] = []  # things the model chose to flag rather than edit

    def is_empty(self) -> bool:
        return not self.repairs and not self.issues and not self.summary.strip()


class AppliedRepair(StrictModel):
    find: str
    replace: str
    count: int
    reason: str = ""
    kind: str = "notation"


class RejectedRepair(StrictModel):
    find: str
    replace: str
    why: str


def _edit_allowed(edit: ScriptRepair, copyedit: bool) -> tuple[bool, str]:
    """Per-kind gate. NOTATION keeps its trusted scope (the original behavior). Author-text and
    artifact edits must clear the deterministic copy-edit guard, and only when copy-edit is on.
    A `data`/claim edit is never auto-applied - it belongs in `issues` for human review."""
    if edit.kind == "data":
        return False, "data/claim - flag only, never auto-fixed"
    if edit.kind in _GUARDED_KINDS:
        if not copyedit:
            return False, "copy-edit disabled (--as-written): only notation is fixed"
        if not copyedit_guard(edit.find, edit.replace):
            return False, "copy-edit guard: would change a number, polarity, or claim"
    return True, ""  # notation (or default) - trusted scope


def candidate_repairs(
    script_text: str, repairs: list[ScriptRepair], *, copyedit: bool = False
) -> tuple[list[ScriptRepair], list[RejectedRepair]]:
    """Keep the repairs that can actually be applied: a non-empty, localized find that is a
    verbatim substring of the script AND passes the per-kind gate (notation trusted; author/artifact
    edits must clear the copy-edit guard when copy-edit is on; data is flag-only). Returns
    (candidates, rejected) where rejected covers both un-applicable and guard-blocked edits."""
    candidates: list[ScriptRepair] = []
    rejected: list[RejectedRepair] = []
    for edit in sorted(repairs, key=lambda e: len(e.find), reverse=True):
        if not edit.find.strip() or edit.find == edit.replace or len(edit.find) > _MAX_SPAN:
            rejected.append(
                RejectedRepair(
                    find=edit.find, replace=edit.replace, why="empty, a no-op, or too long a span"
                )
            )
            continue
        if edit.find not in script_text:
            rejected.append(
                RejectedRepair(find=edit.find, replace=edit.replace, why="not found in script")
            )
            continue
        allowed, why = _edit_allowed(edit, copyedit)
        if not allowed:
            rejected.append(RejectedRepair(find=edit.find, replace=edit.replace, why=why))
            continue
        candidates.append(edit)
    return candidates, rejected


def apply_one(chunks: list[Chunk], edit: ScriptRepair) -> int:
    """Apply one edit to the chunk texts in place, on WHOLE-TOKEN matches only (word boundaries),
    so a short find never rewrites the inside of a word ("mm" leaves "committee" alone). Editing
    chunks (not the flat script) preserves each chunk's block_ids, so provenance survives. Returns
    the number of replacements."""
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(edit.find) + r"(?![A-Za-z0-9])")
    count = 0
    for chunk in chunks:
        chunk.text, n = pattern.subn(edit.replace, chunk.text)
        count += n
    return count


_NOTATION_DO = (
    "- units/symbols spoken as letters or left abbreviated -> full spoken words: 'cm' -> "
    "'centimeters', 'L over min' -> 'liters per minute', a unit 'omega' -> 'ohms', 'mV over "
    "V' -> 'millivolts per volt'. (kind: notation)\n"
    "- leaked LaTeX/markup or a leaked variable/notation string -> its spoken form (or remove "
    "the leaked tag). (kind: notation or extraction_artifact)\n"
    "- a chemical formula read as letters -> the compound name where clearly intended: 'S iO "
    "two' -> 'silicon dioxide'. (kind: notation)\n"
    "- number/ordinal spacing artifacts: 'thirty th' -> 'thirtieth'. (kind: notation)\n"
)
_RETURN_JSON = (
    "Return ONLY this JSON:\n"
    '{"summary":"one-paragraph assessment","repairs":[{"find":"exact substring with context",'
    '"replace":"the same content with the one problem fixed","reason":"what was wrong",'
    '"kind":"notation|spelling|grammar|spacing|extraction_artifact"}],'
    '"issues":[{"kind":"broken_gloss|ocr_garble|truncation|suspected_data_error|other",'
    '"severity":"high|medium|low","location":"short quote","detail":"...","suggestion":"..."}]}'
)


def build_script_repair_prompt(script: str, *, copyedit: bool = False) -> str:
    if not copyedit:
        return (
            "Below is the FINAL audiobook narration script generated from a scientific thesis. "
            "Propose small find/replace edits that fix how NOTATION is SPOKEN.\n\n"
            "DO fix (put in 'repairs', kind 'notation'):\n" + _NOTATION_DO + "\n"
            "DO NOT touch - read it EXACTLY as written, it is the author's text, not yours to "
            "fix:\n"
            "- spelling mistakes ('preparaing', 'stomotal') and hyphenation - leave them.\n"
            "- grammar or awkward sentences - leave them.\n"
            "- pronunciation of ordinary words or proper names - do NOT add phonetic respellings.\n"
            "- punctuation and parentheses around the notation - KEEP them.\n"
            "Keep every number, value, name, claim, and all punctuation exactly as it appears; "
            "change only how the notation token is voiced.\n\n"
            "'find' MUST be an exact substring of the script - copy a few words verbatim WITH "
            "enough surrounding context to be unambiguous (never a bare token like 'mm'), short "
            "and localized.\n\n" + _RETURN_JSON + "\n\n=== SCRIPT ===\n"
            f"{script}\n"
        )
    return (
        "Below is the FINAL audiobook narration script generated from a scientific thesis. Propose "
        "small find/replace edits so it reads cleanly aloud, and TAG each with its `kind`.\n\n"
        "DO fix (put in 'repairs'):\n" + _NOTATION_DO + "- a clearly MISSPELLED word (a non-word) "
        "-> its intended real word: 'stomotal' -> 'stomatal', 'preparaing' -> 'preparing'. (kind: "
        "spelling)\n"
        "- subject-verb agreement, a wrong tense, OR readability: add a function word ('in' before "
        "a unit) or turn a stray unit-parenthesis into commas so a measurement reads cleanly, e.g. "
        "'R s megapascals seconds per kilogram )' -> 'R s, in megapascals seconds per kilogram,'. "
        "(kind: grammar)\n"
        "- fused words or missing/extra spacing: 'withincreasing' -> 'with increasing'. (kind: "
        "spacing)\n"
        "- a PDF-extraction leak that is not the author's intent (stray operator, leaked tag). "
        "(kind: extraction_artifact)\n\n"
        "DO NOT (these change meaning - they are NOT edits, put any you suspect in 'issues'):\n"
        "- NEVER change a number, value, sign, unit, or measurement.\n"
        "- NEVER add or remove a negation or scope word (not, no, only, all, more, less).\n"
        "- NEVER insert a claim or hedge ('significant'), drop a content word, or PARAPHRASE / "
        "swap a content word (readability adds only function words/punctuation).\n"
        "- a SUSPECTED number/sign/unit or factual error -> put it in 'issues' as "
        "'suspected_data_error'; do not edit it.\n"
        "Make the MINIMAL edit: `replace` = `find` with ONLY the one flagged problem fixed, every "
        "other character kept.\n\n"
        "'find' MUST be an exact substring of the script - copy a few words verbatim WITH enough "
        "surrounding context to be unambiguous, short and localized.\n\n"
        + _RETURN_JSON
        + "\n\n=== SCRIPT ===\n"
        f"{script}\n"
    )


def parse_script_repair_plan(raw: str) -> ScriptRepairPlan:
    """Parse the model's JSON; an empty plan on any failure (so the offline mock is a no-op)."""
    text = raw
    for fence in ("```json", "```"):
        text = text.replace(fence, "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return ScriptRepairPlan()
    try:
        data: Any = json.loads(text[start : end + 1])
        return ScriptRepairPlan.model_validate(data)
    except Exception:  # noqa: BLE001 - malformed model output -> no repair, not a crash
        return ScriptRepairPlan()


def render_script_repair_report(
    plan: ScriptRepairPlan, applied: list[AppliedRepair], rejected: list[RejectedRepair]
) -> str:
    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = ["# Script repair report (notation vocalization)", ""]
    if plan.summary.strip():
        lines += [plan.summary.strip(), ""]
    lines += [f"## Applied repairs ({len(applied)})", ""]
    if applied:
        lines += ["| find | replace | times | reason |", "|---|---|---|---|"]
        lines += [
            f"| {cell(a.find)} | {cell(a.replace)} | {a.count} | {cell(a.reason)} |"
            for a in applied
        ]
    else:
        lines.append("None.")
    lines += ["", f"## Not applied ({len(rejected)}) - could not be located in the script", ""]
    if rejected:
        lines += ["| find | proposed replace | why |", "|---|---|---|"]
        lines += [f"| {cell(r.find)} | {cell(r.replace)} | {cell(r.why)} |" for r in rejected]
    else:
        lines.append("None.")
    if plan.issues:
        lines += ["", "## Flagged by the model (not edited)", ""]
        lines += [
            f"- **{cell(i.severity)}/{cell(i.kind)}** {cell(i.location)}: {cell(i.detail)}"
            for i in plan.issues
        ]
    return "\n".join(lines) + "\n"
