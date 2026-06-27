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
