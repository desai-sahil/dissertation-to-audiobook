from __future__ import annotations

import pytest

from thesis_audiobook.lexicon import DEFAULT_LEXICON
from thesis_audiobook.normalization.acronyms import expand_acronyms


@pytest.mark.parametrize(
    "raw,spoken",
    [
        ("ABA", "abscisic acid"),
        ("ROS", "reactive oxygen species"),
        ("VPD", "vapor pressure deficit"),
        ("MCMC", "M C M C"),
        ("WT", "wild type"),
    ],
)
def test_expand_acronyms(raw: str, spoken: str) -> None:
    assert expand_acronyms(raw, DEFAULT_LEXICON) == spoken
