from __future__ import annotations

from thesis_audiobook.faithfulness import (
    AUDIT_FRAMINGS,
    AuditVerdict,
    build_audit_prompt,
    panel_faithful,
    parse_audit_verdict,
)


def test_prompt_grounds_on_anchor_and_output() -> None:
    prompt = build_audit_prompt(
        "R = 8.314 J", "R equals eight point three one four joules", "focus"
    )
    assert "8.314" in prompt and "eight point three one four" in prompt and "focus" in prompt


def test_parse_is_fail_closed() -> None:
    assert parse_audit_verdict('{"faithful": true, "reason": "ok"}').faithful is True
    assert parse_audit_verdict('{"faithful": false}').faithful is False
    # any unreadable response defaults to UNFAITHFUL, never applied on a verdict we cannot read
    assert parse_audit_verdict("the model rambled without json").faithful is False
    assert parse_audit_verdict("").faithful is False
    assert parse_audit_verdict("```json\n{bad json}\n```").faithful is False


def test_panel_requires_unanimous_full_panel() -> None:
    n = len(AUDIT_FRAMINGS)
    faithful = AuditVerdict(faithful=True)
    unfaithful = AuditVerdict(faithful=False)
    assert panel_faithful([faithful] * n) is True
    assert panel_faithful([faithful] * (n - 1) + [unfaithful]) is False  # one veto blocks
    assert panel_faithful([faithful] * (n - 1)) is False  # short panel (a call dropped) blocks
    assert panel_faithful([]) is False
