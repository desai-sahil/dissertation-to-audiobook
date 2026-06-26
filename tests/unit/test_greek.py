from __future__ import annotations

import pytest

from thesis_audiobook.lexicon import DEFAULT_LEXICON
from thesis_audiobook.normalization.greek import expand_greek, expand_greek_letters


@pytest.mark.parametrize(
    "raw,spoken",
    [
        ("ψ", " psi "),
        ("δ", " delta "),
        ("μ", " mu "),
        ("α", " alpha "),
        ("Δ", " delta "),
        ("Σ", " sigma "),
    ],
)
def test_letter_names_exact(raw: str, spoken: str) -> None:
    assert expand_greek_letters(raw) == spoken


def test_domain_expansion_wins() -> None:
    assert expand_greek("psi_xyl", DEFAULT_LEXICON) == "xylem water potential"
