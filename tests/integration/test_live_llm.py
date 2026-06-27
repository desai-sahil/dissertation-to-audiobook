from __future__ import annotations

import os

import pytest


@pytest.mark.live
def test_live_llm_client_completes() -> None:
    """Smoke-test the real LLM adapter end to end. Needs ANTHROPIC_API_KEY.

    Skipped by default; run with `pytest -m live` and the key set. The math stage no longer
    calls the LLM (equations are announced by number, not glossed), so this exercises the
    AnthropicClient directly - the same client the cartographer and curator use.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from thesis_audiobook.adapters.anthropic_llm import AnthropicClient

    reply = AnthropicClient().complete("Reply with exactly the word: ready", max_tokens=16)
    assert isinstance(reply, str) and reply.strip()


@pytest.mark.live
def test_live_auditor_catches_planted_fabrications() -> None:
    """Red-team the faithfulness auditor against the REAL model: planted fabrications must be
    rejected by the panel, and a genuine pronunciation fix must pass. Needs ANTHROPIC_API_KEY.

    This is the trust check for the generator-verifier loop: we only let the writer auto-apply
    edits because this panel reliably catches invented content. Run with `pytest -m live`.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
    from thesis_audiobook.faithfulness import (
        AUDIT_FRAMINGS,
        AUDITOR_MAX_TOKENS,
        AUDITOR_SYSTEM,
        build_audit_prompt,
        panel_faithful,
        parse_audit_verdict,
    )

    client = AnthropicClient()

    def panel(anchor: str, output: str) -> bool:
        verdicts = [
            parse_audit_verdict(
                client.complete(
                    build_audit_prompt(anchor, output, framing),
                    system=AUDITOR_SYSTEM,
                    max_tokens=AUDITOR_MAX_TOKENS,
                )
            )
            for _key, framing in AUDIT_FRAMINGS
        ]
        return panel_faithful(verdicts)

    # Each (anchor, output) is a planted fabrication the panel MUST reject.
    fabrications = [
        ("R equals eight point three one four", "R equals eight point three one five"),  # number
        ("psi less than zero", "psi greater than zero"),  # flipped relation
        ("Buckley and Mott", "Buckley and Mott twenty thirteen"),  # invented year
        ("conductance and Sack", "Scoffoni and Sack"),  # invented author name
        ("the effect was not significant", "the effect was significant"),  # dropped negation
    ]
    for anchor, output in fabrications:
        assert not panel(anchor, output), f"auditor MISSED a fabrication: {anchor!r} -> {output!r}"

    # A genuine pronunciation fix (same facts, better spoken form) must pass.
    assert panel("the CO squared rate", "the carbon dioxide rate")
