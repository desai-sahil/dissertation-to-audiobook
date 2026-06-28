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
def test_live_script_repair_vocalizes_notation() -> None:
    """The real writer proposes notation-vocalization edits, scoped to NOT touch the author's
    spelling. Needs ANTHROPIC_API_KEY; run with `pytest -m live`.

    We give a script with a unit abbreviation, a leaked symbol, and a deliberate author typo, and
    check the model proposes a localized edit for the notation while leaving the typo alone.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
    from thesis_audiobook.script_repair import (
        SCRIPT_REPAIR_MAX_TOKENS,
        SCRIPT_REPAIR_SYSTEM,
        build_script_repair_prompt,
        candidate_repairs,
        parse_script_repair_plan,
    )

    script = (
        "The sample was held at twenty five cm depth for ten mins. We then measured the "
        "responce at five mm intervals across the leaf surface."
    )
    raw = AnthropicClient().complete(
        build_script_repair_prompt(script),
        system=SCRIPT_REPAIR_SYSTEM,
        max_tokens=SCRIPT_REPAIR_MAX_TOKENS,
    )
    plan = parse_script_repair_plan(raw)
    candidates, _ = candidate_repairs(script, plan.repairs)
    replaces = " ".join(c.replace for c in candidates).lower()
    # a unit abbreviation should be vocalized somewhere in the proposed edits
    assert "centimeters" in replaces or "millimeters" in replaces or "minutes" in replaces
    # the author's misspelling "responce" must NOT be "corrected" to "response"
    assert not any("response" in c.replace.lower() for c in candidates)
