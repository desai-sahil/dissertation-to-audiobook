"""Faithfulness auditors: independent, grounded verifiers that a script edit invented nothing.

The script repair (the "writer") proposes find->replace edits; before any edit is applied it must
pass the deterministic no-fabrication guard AND a panel of independent auditors. Each auditor is a
separate, narrow, GROUNDED check: it sees ONLY the anchor (the verbatim source the edit replaces)
and the proposed spoken output, and answers faithful/unfaithful - defaulting to UNFAITHFUL on any
doubt or parse failure (fail-closed). An edit is applied only if EVERY auditor says faithful.

Grounding the auditor on the anchor is what makes a second model genuinely reduce fabrication
instead of rubber-stamping: comparing two short strings ("does SPOKEN add/drop/alter a fact vs
ORIGINAL?") is a checkable comparison, not open-ended judgement. The two auditors use different
adversarial framings so they are independent calls (and cache to distinct results), covering what
the deterministic guard cannot - a flipped claim or relation that adds no new number or name. Pure:
prompts, parsing, panel rule; the cached model calls live in the stage.
"""

from __future__ import annotations

import json
from typing import Any

from thesis_audiobook.ir import StrictModel

AUDITOR_VERSION = "auditor-v2"  # bump invalidates cached verdicts when the prompt changes
AUDITOR_SYSTEM = (
    "You audit one audiobook edit. The edit re-renders WRITTEN text - symbols, math notation, "
    "chemical formulas, units, abbreviations - into SPOKEN words. Re-rendering the SAME content "
    "in different words is FAITHFUL and is the whole point; judge by what each form DENOTES, "
    "using your domain knowledge. An edit is UNFAITHFUL only when the spoken form changes the "
    "CONTENT: a different numeric value or unit, a flipped relation or direction (more vs less, "
    "increase vs decrease, a dropped or added negation), or a different named entity. Do not flag "
    "a mere difference in WORDING for the same thing; do flag any real change in WHAT is said. "
    "Calibration: 'CO squared' -> 'carbon dioxide' FAITHFUL (same compound, CO2); 'g s' -> "
    "'stomatal conductance' FAITHFUL (the symbol's meaning); 'eight point three one four' -> "
    "'eight point three one five' UNFAITHFUL (value changed); 'less than' -> 'greater than' "
    "UNFAITHFUL (relation flipped); 'not significant' -> 'significant' UNFAITHFUL (negation "
    "dropped); 'Mott' -> 'Mott twenty thirteen' UNFAITHFUL (a year was added). Return ONLY the "
    "requested JSON object; no prose, no markdown fences."
)
AUDITOR_MAX_TOKENS = 400

# Two independent framings -> two distinct cached calls per edit. Both must pass.
AUDIT_FRAMINGS: list[tuple[str, str]] = [
    (
        "extract",
        "List what ORIGINAL denotes (each value, unit, name, and the core claim or relation), "
        "then what SPOKEN denotes. Are they the SAME content, only re-worded for the ear? It is "
        "unfaithful only if a value, unit, relation, negation, or named entity actually differs.",
    ),
    (
        "skeptic",
        "Hunt for a real change of CONTENT, not of form: does SPOKEN state a different value or "
        "unit, flip a relation or negation, or name a different entity than ORIGINAL? Re-saying "
        "the same quantity in words (a formula as its name, a symbol as its word) is NOT a "
        "change. Unfaithful only if WHAT is said changed, not merely HOW.",
    ),
]


class AuditVerdict(StrictModel):
    faithful: bool = False  # fail-closed: default reject
    offending: str = ""
    reason: str = ""


def build_audit_prompt(anchor: str, output: str, framing: str) -> str:
    return (
        "An audiobook edit re-renders written text into spoken words. It must keep the same "
        "content; it may change only how that content is worded for the ear.\n\n"
        f"ORIGINAL: {anchor}\n"
        f"SPOKEN:   {output}\n\n"
        f"{framing}\n\n"
        'Return ONLY: {"faithful": true or false, "offending": "the changed content, or empty", '
        '"reason": "one short clause"}'
    )


def parse_audit_verdict(raw: str) -> AuditVerdict:
    """Parse the model's JSON verdict. Fail closed: any malformed/empty response -> UNFAITHFUL, so
    an edit is never applied on a verdict we could not actually read."""
    text = raw
    for fence in ("```json", "```"):
        text = text.replace(fence, "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return AuditVerdict(faithful=False, reason="unparseable verdict (fail-closed)")
    try:
        data: Any = json.loads(text[start : end + 1])
        return AuditVerdict.model_validate(data)
    except Exception:  # noqa: BLE001 - malformed verdict -> reject, never a crash
        return AuditVerdict(faithful=False, reason="unparseable verdict (fail-closed)")


def panel_faithful(verdicts: list[AuditVerdict]) -> bool:
    """An edit is faithful only if the full panel ran and EVERY auditor passed (unanimous)."""
    return len(verdicts) == len(AUDIT_FRAMINGS) and all(v.faithful for v in verdicts)
