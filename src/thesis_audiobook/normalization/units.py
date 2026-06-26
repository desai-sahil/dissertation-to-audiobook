"""Units and chemistry. Pure, deterministic, no I/O.

Runs before the numbers module so chemical formulae (CO2, Ca2+) are consumed as whole
tokens rather than having their digits spelled. Both ASCII and common PDF-unicode
forms are matched. The table is curated and extended via the lexicon over time.
"""

from __future__ import annotations

import re

# Longest first so compound units win. Each pair is (raw, spoken).
_UNIT_TABLE: list[tuple[str, str]] = [
    ("µmol m^-2 s^-1", "micromoles per meter squared per second"),
    ("umol m^-2 s^-1", "micromoles per meter squared per second"),
    ("μmol m⁻² s⁻¹", "micromoles per meter squared per second"),
    ("µmol m⁻² s⁻¹", "micromoles per meter squared per second"),
    ("mol m^-2 s^-1", "moles per meter squared per second"),
    ("m^-2 s^-1", "per meter squared per second"),
    ("m⁻² s⁻¹", "per meter squared per second"),
    ("H2O2", "hydrogen peroxide"),
    ("H₂O₂", "hydrogen peroxide"),
    ("Ca2+", "calcium ion"),
    ("Ca²⁺", "calcium ion"),
    ("Na+", "sodium ion"),
    ("K+", "potassium ion"),
    ("Cl-", "chloride ion"),
    ("Cl−", "chloride ion"),
    ("CO2", "C O two"),
    ("CO₂", "C O two"),
    ("O2", "O two"),
    ("H2O", "water"),
    ("H₂O", "water"),
    ("MPa", "megapascals"),
    ("kPa", "kilopascals"),
    ("°C", "degrees Celsius"),
    ("µM", "micromolar"),
    ("μM", "micromolar"),
    ("mM", "millimolar"),
    ("µm", "micrometers"),
    ("μm", "micrometers"),
    ("µg", "micrograms"),
    ("μg", "micrograms"),
    ("µL", "microliters"),
    ("μL", "microliters"),
    ("s^-1", "per second"),
    ("s⁻¹", "per second"),
    ("m^-2", "per meter squared"),
    ("m⁻²", "per meter squared"),
    ("µmol", "micromoles"),
    ("μmol", "micromoles"),
]


def normalize_units(text: str) -> str:
    for raw, spoken in _UNIT_TABLE:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(raw)}(?![A-Za-z0-9])"
        text = re.sub(pattern, lambda _m, value=spoken: value, text)
    return text
