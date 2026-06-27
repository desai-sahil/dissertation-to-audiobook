"""Guarded, claim-safe repair of the narration SCRIPT (pure core).

The phase-4 script QC flags read-aloud defects but never edits (claim-safety). This module is
the safe auto-fix layer that mirrors the extraction repair: the model proposes {find -> replace}
pronunciation/normalization swaps, and we apply ONLY the ones that pass a no-fabrication guard,
deterministically (the model call is cached, so a given script repairs identically). The script
QC then re-audits the repaired script, so the gate reflects the post-repair state.

The guard is the safety invariant. Unlike the extraction repair (which preserves the exact word
sequence), a SCRIPT repair is allowed to change words - that is the point ("CO squared" ->
"carbon dioxide", "mm" -> "millimeters"). What it must NEVER do is fabricate content: introduce a
number, a year, or a proper name the model cannot actually verify. So an edit is applied only if
its replacement adds no FACTUAL token (a digit-bearing word, a spoken number/ordinal word, or a
capitalized proper noun) that is not already in the text it replaces. This auto-applies pure
pronunciation fixes and rejects every reconstruction - a guessed number ("...eight hundred
four..." -> "...eight zero four..."), a fabricated citation year ("Buckley and Mott" -> "Buckley
and Mott twenty thirteen"), an asserted name ("& Sack" -> "Scoffoni and Sack"), or a cross-
reference change ("first chapter" -> "second chapter"). Those go to human review, never applied.
This module is pure; the cached model call and file writes live in the stage and the CLI.
"""

from __future__ import annotations

import json
import re
from typing import Any

from thesis_audiobook.extraction_qc import ExtractionIssue
from thesis_audiobook.ir import Chunk, StrictModel

SCRIPT_REPAIR_VERSION = "scriptrepair-v1"
SCRIPT_REPAIR_SYSTEM = (
    "You repair how an AUDIOBOOK NARRATION SCRIPT is pronounced. Propose only small find/replace "
    "swaps that fix how EXISTING text reads aloud. NEVER invent content: do not add or change a "
    "number, a year, or a name, and do not reconstruct anything garbled - flag those instead. "
    "Return ONLY the requested JSON; no prose, no markdown fences."
)
SCRIPT_REPAIR_MAX_TOKENS = 16_384
_MAX_SPAN = 120  # a find longer than this is reported, not auto-applied (keeps edits localized)

# Spoken number / ordinal words. Adding one in a replacement is treated as fabricating a value or
# year, so it is rejected by the guard.
_NUMBER_WORDS = frozenset(
    [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "thousand",
        "million",
        "billion",
        "trillion",
        "point",
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "sixth",
        "seventh",
        "eighth",
        "ninth",
        "tenth",
        "eleventh",
        "twelfth",
    ]
)
_WORD = re.compile(r"[\w']+")


def _factual_tokens(text: str) -> set[str]:
    """Lower-cased tokens that assert a fact: digit-bearing words, spoken number/ordinal words,
    and capitalized proper nouns (len >= 2, not an all-caps acronym/symbol)."""
    tokens: set[str] = set()
    for word in _WORD.findall(text):
        lower = word.lower()
        is_number = lower in _NUMBER_WORDS or any(ch.isdigit() for ch in word)
        is_proper = len(word) >= 2 and word[0].isupper() and not word.isupper()
        if is_number or is_proper:
            tokens.add(lower)
    return tokens


def is_safe_script_repair(find: str, replace: str) -> bool:
    """True iff find->replace cannot fabricate content: the replacement introduces no factual
    token (number/year/name) absent from the text it replaces. A pure pronunciation swap passes;
    any reconstruction of a number, year, or name is rejected."""
    if not find.strip() or find == replace or len(find) > _MAX_SPAN:
        return False
    return _factual_tokens(replace) <= _factual_tokens(find)


class ScriptRepair(StrictModel):
    find: str  # exact substring of the script that reads wrong
    replace: str  # the corrected spoken form (same facts, better pronunciation)
    reason: str = ""


class ScriptRepairPlan(StrictModel):
    summary: str = ""
    repairs: list[ScriptRepair] = []
    issues: list[ExtractionIssue] = []  # defects that need human review, not auto-fixable

    def is_empty(self) -> bool:
        return not self.repairs and not self.issues and not self.summary.strip()


class AppliedRepair(StrictModel):
    find: str
    replace: str
    count: int
    reason: str = ""


class RejectedRepair(StrictModel):
    find: str
    replace: str
    why: str


def apply_script_repairs(
    chunks: list[Chunk], repairs: list[ScriptRepair]
) -> tuple[list[AppliedRepair], list[RejectedRepair]]:
    """Apply guard-passing, locatable repairs to chunk texts in place (all occurrences), longest
    find first so a shorter edit cannot partially clobber a longer one. Editing chunks (not the
    flat script) preserves each chunk's block_ids, so provenance survives. Returns (applied,
    rejected)."""
    applied: list[AppliedRepair] = []
    rejected: list[RejectedRepair] = []
    for edit in sorted(repairs, key=lambda e: len(e.find), reverse=True):
        if not is_safe_script_repair(edit.find, edit.replace):
            rejected.append(
                RejectedRepair(
                    find=edit.find,
                    replace=edit.replace,
                    why="would fabricate content (a number, year, or name) or span too large",
                )
            )
            continue
        count = sum(chunk.text.count(edit.find) for chunk in chunks)
        if count == 0:
            rejected.append(
                RejectedRepair(find=edit.find, replace=edit.replace, why="not found in script")
            )
            continue
        for chunk in chunks:
            if edit.find in chunk.text:
                chunk.text = chunk.text.replace(edit.find, edit.replace)
        applied.append(
            AppliedRepair(find=edit.find, replace=edit.replace, count=count, reason=edit.reason)
        )
    return applied, rejected


def build_script_repair_prompt(script: str) -> str:
    return (
        "Below is the FINAL audiobook narration script generated from a scientific thesis. "
        "Propose small fixes for how EXISTING text reads aloud, and separately flag defects you "
        "must NOT auto-fix.\n\n"
        "Safe to repair (put in 'repairs'): a wrong pronunciation/notation of text that is "
        "already present - 'CO squared' -> 'carbon dioxide', 'mm' -> 'millimeters', 'H two "
        "degrees' -> 'water', a leaked symbol -> its spoken word. RULE: 'replace' must contain "
        "NO number, year, or name that is not already in 'find'. You may only change HOW the "
        "existing words sound; never add a value, a citation year, or an author/proper name, and "
        "never reconstruct something garbled. 'find' must be an EXACT substring of the script "
        "(copy it verbatim, a few words), short and localized.\n\n"
        "NOT safe to auto-fix (put in 'issues', do not invent a 'replace'): a garbled number to "
        "restore, a missing citation year or author, a wrong cross-reference, truncated content, "
        "anything where the correct text is uncertain.\n\n"
        "Return ONLY this JSON:\n"
        '{"summary":"one-paragraph assessment","repairs":[{"find":"exact substring",'
        '"replace":"same facts, better pronunciation","reason":"what was wrong"}],'
        '"issues":[{"kind":"broken_gloss|citation_error|ocr_garble|truncation|other",'
        '"severity":"high|medium|low","location":"short quote","detail":"...","suggestion":"..."}]}'
        "\n\n=== SCRIPT ===\n"
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

    lines = ["# Script repair report (guarded auto-fix)", ""]
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
    lines += ["", f"## Rejected ({len(rejected)}) - NOT applied (guard or not found)", ""]
    if rejected:
        lines += ["| find | proposed replace | why |", "|---|---|---|"]
        lines += [f"| {cell(r.find)} | {cell(r.replace)} | {cell(r.why)} |" for r in rejected]
    else:
        lines.append("None.")
    if plan.issues:
        lines += ["", "## Flagged for human review (not auto-fixable)", ""]
        lines += [
            f"- **{cell(i.severity)}/{cell(i.kind)}** {cell(i.location)}: {cell(i.detail)}"
            for i in plan.issues
        ]
    return "\n".join(lines) + "\n"
