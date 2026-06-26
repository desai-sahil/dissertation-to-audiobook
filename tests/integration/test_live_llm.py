from __future__ import annotations

import os

import pytest


@pytest.mark.live
def test_live_equation_gloss() -> None:
    """Glosses one real equation against the real LLM. Needs ANTHROPIC_API_KEY.

    Skipped by default; run with `pytest -m live` and the key set.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
    from thesis_audiobook.stages.math import gloss_prompt

    gloss = AnthropicClient().complete(gloss_prompt(r"g_s = \frac{A}{c_a - c_i}"))
    assert isinstance(gloss, str)
    assert gloss.strip()
    # The system prompt forbids reading LaTeX/symbols aloud: a faithful gloss speaks
    # the meaning, so the raw markup must not survive into the spoken sentence.
    for raw in ("\\frac", "g_s", "c_a", "^", "_", "{", "}"):
        assert raw not in gloss
