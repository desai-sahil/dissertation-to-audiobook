from __future__ import annotations

import pytest

from thesis_audiobook.lexicon import DEFAULT_LEXICON
from thesis_audiobook.normalization import normalize_all

L = DEFAULT_LEXICON


@pytest.mark.parametrize(
    "raw,spoken",
    [
        # Numbers and stats.
        ("37%", "thirty-seven percent"),
        ("p<0.05", "p less than zero point zero five"),
        ("n=6", "n equals six"),
        ("5.2 ± 0.3", "five point two, plus or minus, zero point three"),
        ("10^-3", "ten to the minus three"),
        ("R^2", "R squared"),
        ("0.3-0.5", "zero point three to zero point five"),
        ("2-8", "two to eight"),
        # Units and chemistry.
        ("CO2", "C O two"),
        ("Ca2+", "calcium ion"),
        ("H2O", "water"),
        ("MPa", "megapascals"),
        ("umol m^-2 s^-1", "micromoles per meter squared per second"),
        # Symbols, greek, genes, acronyms.
        ("gs", "stomatal conductance"),
        ("psi_xyl", "xylem water potential"),
        ("psi_ssc^apo", "apoplastic subsidiary-cell water potential"),
        ("slac1", "slac one"),
        ("GhSLAC1", "G H slac one"),
        ("osca1", "osca one"),
        ("ABA", "abscisic acid"),
        ("ROS", "reactive oxygen species"),
        ("MCMC", "M C M C"),
        ("VPD", "vapor pressure deficit"),
    ],
)
def test_chapter6_cases(raw: str, spoken: str) -> None:
    assert normalize_all(raw, L) == spoken


@pytest.mark.parametrize(
    "raw,spoken",
    [
        ("a C3 crop", "a C three crop"),
        ("feedback via A8H", "feedback via A eight H"),
        ("CYP707A enzymes", "CYP seven zero seven A enzymes"),
        ("56mM", "fifty-six millimolar"),
        ("10 µm", "ten micrometers"),
    ],
)
def test_identifier_and_quantity_digits(raw: str, spoken: str) -> None:
    # Identifier digits read digit-by-digit; a quantity glued to a unit reads as a
    # cardinal. Real Chapter 6 tokens the synthetic fixture missed.
    assert normalize_all(raw, L) == spoken


def test_unicode_minus_does_not_leak() -> None:
    out = normalize_all("psi_xyl−VPD", L)
    assert "−" not in out
    assert out == "xylem water potential-vapor pressure deficit"


def test_url_becomes_listenable_placeholder() -> None:
    out = normalize_all("See https://desai-sahil.github.io/x/ for more.", L)
    assert "the link in the text" in out
    assert "http" not in out
