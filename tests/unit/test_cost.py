from __future__ import annotations

from thesis_audiobook.cost import estimate_cost


def test_cost_is_deterministic_and_linear() -> None:
    first = estimate_cost("hello", 0.01)
    second = estimate_cost("hello", 0.01)
    assert first == second
    assert first.characters == 5
    assert first.estimated_usd == round(5 * 0.01, 4)


def test_cost_scales_with_length() -> None:
    short = estimate_cost("x", 0.01)
    long = estimate_cost("x" * 100, 0.01)
    assert long.estimated_usd > short.estimated_usd
