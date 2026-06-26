from __future__ import annotations

import pytest

from thesis_audiobook.normalization.stats import normalize_stats


@pytest.mark.parametrize(
    "raw,spoken",
    [
        ("p<0.05", "p less than 0.05"),
        ("a>b", "a greater than b"),
        ("n=6", "n equals 6"),
        ("a/b", "a over b"),
        ("*p", " asterisk p"),
    ],
)
def test_normalize_stats(raw: str, spoken: str) -> None:
    assert normalize_stats(raw) == spoken


def test_plus_minus_becomes_phrase() -> None:
    # Operator pass only; whitespace is tidied later in normalize_all.
    assert ", plus or minus," in normalize_stats("5.2 ± 0.3")
