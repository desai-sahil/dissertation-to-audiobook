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

AUDITOR_VERSION = "auditor-v1"
AUDITOR_SYSTEM = (
    "You audit a single audiobook edit for faithfulness. An edit may change only HOW text is "
    "spoken, never the facts. You are adversarial: if the spoken form asserts anything the "
    "original does not support, it is UNFAITHFUL. When in any doubt, answer unfaithful. Return "
    "ONLY the requested JSON object; no prose, no markdown fences."
)
AUDITOR_MAX_TOKENS = 400

# Two independent framings -> two distinct cached calls per edit. Both must pass.
AUDIT_FRAMINGS: list[tuple[str, str]] = [
    (
        "extract",
        "List the facts in ORIGINAL (every number, value, unit, name, citation, and the core "
        "claim/relation), then the facts in SPOKEN. If SPOKEN adds, drops, or alters ANY fact, "
        "it is unfaithful.",
    ),
    (
        "skeptic",
        "Try to find one thing SPOKEN says that ORIGINAL does not support - a changed number or "
        "unit, an added or altered name, a flipped relation (increase vs decrease, a negation, "
        "'significant' vs 'not significant'), or any invented content. If you find one, it is "
        "unfaithful.",
    ),
]


class AuditVerdict(StrictModel):
    faithful: bool = False  # fail-closed: default reject
    offending: str = ""
    reason: str = ""


def build_audit_prompt(anchor: str, output: str, framing: str) -> str:
    return (
        "An audiobook edit changes only how existing text is PRONOUNCED, never its facts.\n\n"
        f"ORIGINAL: {anchor}\n"
        f"SPOKEN:   {output}\n\n"
        f"{framing}\n\n"
        'Return ONLY: {"faithful": true or false, "offending": "the changed fact, or empty", '
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
