from __future__ import annotations

import pytest

from thesis_audiobook.normalization.units import normalize_units


@pytest.mark.parametrize(
    "raw,spoken",
    [
        ("CO2", "C O two"),
        ("CO₂", "C O two"),
        ("Ca2+", "calcium ion"),
        ("Ca²⁺", "calcium ion"),
        ("H2O2", "hydrogen peroxide"),
        ("H2O", "water"),
        ("K+", "potassium ion"),
        ("MPa", "megapascals"),
        ("kPa", "kilopascals"),
        ("s^-1", "per second"),
        ("m^-2", "per meter squared"),
        ("umol m^-2 s^-1", "micromoles per meter squared per second"),
    ],
)
def test_normalize_units(raw: str, spoken: str) -> None:
    assert normalize_units(raw) == spoken


def test_unit_respects_word_boundary() -> None:
    # Does not fire inside an unrelated word.
    assert normalize_units("scope") == "scope"
