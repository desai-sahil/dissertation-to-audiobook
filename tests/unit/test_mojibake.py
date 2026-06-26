from __future__ import annotations

import unicodedata

import pytest

from thesis_audiobook.normalization.mojibake import fix_mojibake


@pytest.mark.parametrize(
    "raw,expected",
    [
        # detached diaeresis after a word (the real Jain-thesis defect)
        ("the Scholander ¨ pressure chamber", "the Scholander pressure chamber"),
        ("Forster ¨ distance", "Forster distance"),
        ("Scholander ¨.", "Scholander."),
        # hyphenation split with a stray mark in the gap
        ("the Forster en- ¨ ergy transfer", "the Forster energy transfer"),
        ("Nanofluidics, from bulk to inter- ´ faces", "Nanofluidics, from bulk to interfaces"),
    ],
)
def test_fix_mojibake_strips_detached_marks(raw: str, expected: str) -> None:
    assert fix_mojibake(raw) == expected


def test_fix_mojibake_preserves_genuine_accents() -> None:
    # precomposed accents (attached) are kept; the diaeresis here belongs to the o
    assert fix_mojibake("Schölander pressure chamber") == "Schölander pressure chamber"
    assert fix_mojibake("a café study") == "a café study"
    # decomposed-but-attached accent is recombined (NFC), not stripped
    decomposed = "café"  # e + combining acute
    assert fix_mojibake(decomposed) == "café"


def test_fix_mojibake_noop_on_clean_prose() -> None:
    plain = "The stomata regulate transpiration under drought stress."
    assert fix_mojibake(plain) == plain
    assert fix_mojibake("") == ""
    # result is NFC-normalized
    assert fix_mojibake("normal text") == unicodedata.normalize("NFC", "normal text")
