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

EXTRACTION_REPAIR_VERSION = "extrepair-v2"
EXTRACTION_REPAIR_SYSTEM = (
    "You repair PDF-to-markdown EXTRACTION defects in a scientific thesis. You propose two kinds "
    "of edit. kind 'noise': change ONLY the spaces, detached accents, stray marks, and punctuation "
    "between or around words - keep every word and number exactly as written (same spelling, CASE, "
    "and order), never merge/split words, never rejoin a hyphenated line break, never touch a "
    "number. kind 'artifact': de-shred Marker markup that mangles a value or symbol (a digit split "
    "into per-character <sup> tags, a Miller index written as '< <sup>111</sup> >', glued "
    "notation) by RESTORING it using ONLY the digits and symbols already present in the source - "
    "you may re-render but you must keep the exact same digits in the same order and never drop a "
    "sign (±, °, %). If you cannot restore a value from the digits actually present, do NOT "
    "guess - put it in 'issues'. Return ONLY the requested JSON; no prose, no markdown fences."
)
EXTRACTION_REPAIR_MAX_TOKENS = 16_384
_MAX_SPAN = 400  # an edit longer than this is reported, not auto-applied (limits blast radius)


class RepairEdit(StrictModel):
    broken: str  # exact substring as it appears in the markdown
    fixed: str  # the same text with noise removed, or a de-shredded artifact reconstruction
    reason: str = ""
    kind: str = "noise"  # noise (token-preserving) | artifact (digit-preserving re-render)


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
    kind: str = "noise"


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


# Value-bearing symbols an artifact reconstruction must not drop, invent, or reorder (a decimal
# point is covered by the digit check; these carry meaning on their own). Includes the sign
# (plus-or-minus, ASCII hyphen-minus, U+2212), relational "=" and the ratio "/" - dropping a minus
# flips a sign, dropping "=" or "/" corrupts an equation or ratio. The angle brackets "<" ">" are
# DELIBERATELY excluded: a Miller index "< 111 >" must be able to drop them.
_VALUE_SYMBOLS = ("±", "°", "%", "×", "÷", "=", "/", "-", "−")
_HTML_TAG = re.compile(r"<[^>]*>")


def _ascii_digits(text: str) -> list[str]:
    return [c for c in text if c.isdigit()]


def _letters(text: str) -> set[str]:
    return {c.lower() for c in text if c.isalpha()}


def is_faithful_artifact(broken: str, fixed: str) -> bool:
    """True iff an artifact RECONSTRUCTION restores the author's value from the raw markup without
    inventing one. Unlike is_safe_repair (which forbids any token change), this PERMITS re-rendering
    Marker-shredded notation (e.g. "<sup>0</sup>.1" -> "0.1", "< <sup>111</sup> >" -> "1 1 1"), but
    against the markup with its TAGS STRIPPED it requires: the ORDERED digits identical; every
    value-bearing symbol (sign, degree, percent, times, divide, equals, slash) count-EXACT (never
    dropped OR invented); and no NEW letter introduced (letters may be dropped - a leaked tag, a
    shredded "o" degree - but a variable letter must not be SWAPPED, e.g. C-sub-s -> C-sub-r). So a
    faithful re-render passes while "0.15" -> "0.5", "8.314" -> "314.8", dropping a "±" or a minus,
    or swapping a subscript variable is rejected. Markup tags and the Miller angle brackets carry no
    value and may be removed freely. KNOWN RESIDUAL (ledger-backstopped): because a Miller index
    legitimately splits one digit run ("111" -> "1 1 1"), the check is on the ORDERED digits, not
    digit groups, so merging two separate shredded numbers into one ("12" + "34" -> "1234") is not
    caught here - it relies on the agent's localized-edit instruction and the ledger review."""
    if not broken or broken == fixed or len(broken) > _MAX_SPAN:
        return False
    # Compare the real CONTENT of both sides with markup tags stripped. `fixed` legitimately keeps
    # real markup (a true exponent "10<sup>6</sup>", a subscript "C<sub>p</sub>"); not stripping it
    # would count the tag letters/slash ("</sup>") as content and wrongly reject the reconstruction.
    core = _HTML_TAG.sub("", broken)
    fixed_core = _HTML_TAG.sub("", fixed)
    if _ascii_digits(core) != _ascii_digits(fixed_core):
        return False
    if any(core.count(sym) != fixed_core.count(sym) for sym in _VALUE_SYMBOLS):
        return False
    return _letters(fixed_core) <= _letters(core)


def apply_repairs(
    markdown: str, repairs: list[RepairEdit]
) -> tuple[str, list[AppliedEdit], list[RejectedEdit]]:
    """Apply only guard-passing, locatable edits (all occurrences), longest broken first so a
    shorter edit cannot partially clobber a longer one. Returns (cleaned, applied, rejected)."""
    cleaned = markdown
    applied: list[AppliedEdit] = []
    rejected: list[RejectedEdit] = []
    for edit in sorted(repairs, key=lambda e: len(e.broken), reverse=True):
        if edit.kind == "artifact":
            guard_ok = is_faithful_artifact(edit.broken, edit.fixed)
            guard_why = "would invent, drop, or reorder a value/sign, or span too large"
        else:
            guard_ok = is_safe_repair(edit.broken, edit.fixed)
            guard_why = "would change content (word tokens or case differ) or span too large"
        if not guard_ok:
            rejected.append(RejectedEdit(broken=edit.broken, fixed=edit.fixed, why=guard_why))
            continue
        if edit.broken not in cleaned:
            rejected.append(
                RejectedEdit(broken=edit.broken, fixed=edit.fixed, why="not found in markdown")
            )
            continue
        count = cleaned.count(edit.broken)
        cleaned = cleaned.replace(edit.broken, edit.fixed)
        applied.append(
            AppliedEdit(
                broken=edit.broken,
                fixed=edit.fixed,
                count=count,
                reason=edit.reason,
                kind=edit.kind,
            )
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
        "never change case, never rejoin a hyphenated line break, never alter a number. "
        "'broken' must be an EXACT substring of the markdown (copy it verbatim, a few words "
        "around the defect).\n\n"
        "Also de-shred MARKER ARTIFACTS (put in 'repairs' with kind 'artifact'): notation Marker "
        "split or mangled so it will read wrong aloud. Examples: a decimal split into "
        "per-character superscripts '<sup>0</sup>.1' -> '0.1', '<sup>8</sup>.<sup>314</sup>' -> "
        "'8.314'; a "
        "plus-or-minus '<sup>±</sup> <sup>0</sup>.1' -> '±0.1'; a Miller index "
        "'< <sup>111</sup> >' -> '1 1 1' (drop the angle brackets, read the digits). RULE for "
        "kind 'artifact': RESTORE the value using ONLY the digits/symbols actually present - keep "
        "the SAME digits in the SAME order, never add/drop/reorder a digit, never drop a sign "
        "(±, °, %). If the digits are genuinely lost or ambiguous, do NOT guess - put it "
        "in 'issues'.\n\n"
        "NOT safe to auto-fix (put in 'issues', do not invent a 'fixed'): OCR letter "
        "substitutions, hyphenation splits ('me-asurable'), merged/split words, missing or "
        "truncated content, garbled tables, anything where the correct text is uncertain.\n\n"
        "Return ONLY this JSON:\n"
        '{"summary":"one-paragraph assessment","repairs":[{"broken":"exact substring",'
        '"fixed":"noise removed or artifact restored","reason":"what","kind":"noise|artifact"}],'
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
        lines += ["| kind | broken | fixed | times | reason |", "|---|---|---|---|---|"]
        lines += [
            f"| {cell(a.kind)} | {cell(a.broken)} | {cell(a.fixed)} "
            f"| {a.count} | {cell(a.reason)} |"
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
