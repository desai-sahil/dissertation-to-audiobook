from __future__ import annotations

import os

import pytest


@pytest.mark.live
def test_live_curator_returns_a_plan() -> None:
    """Runs the real curator on a short snippet. Needs ANTHROPIC_API_KEY. Skipped by
    default; run with `pytest -m live`."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
    from thesis_audiobook.curate import build_curate_prompt, parse_plan

    snippet = (
        "We measured abscisic acid (ABA) and vapor pressure deficit (VPD) across genotypes. "
        "ABA rose under drought while the AtRBOHD gene modulated reactive oxygen species."
    )
    plan = parse_plan(AnthropicClient().complete(build_curate_prompt(snippet)))
    assert not plan.is_empty()
    # ABA was defined in-text, so the curator should map it.
    assert any(rule.acronym == "ABA" for rule in plan.acronyms)
