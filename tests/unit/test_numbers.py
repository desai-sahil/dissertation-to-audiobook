from __future__ import annotations

import pytest

from thesis_audiobook.normalization.numbers import (
    int_to_words,
    normalize_numbers,
    number_to_words,
    section_to_words,
    year_to_words,
)


@pytest.mark.parametrize(
    "section,spoken",
    [
        ("6.1", "six point one"),  # matches the old single-dot behavior
        ("2.3.1", "two point three point one"),  # three-level: used to crash number_to_words
        ("6.10", "six point ten"),  # components read as integers, not digits
        ("4", "four"),
        (".", "."),  # degenerate heading does not raise
    ],
)
def test_section_to_words(section: str, spoken: str) -> None:
    assert section_to_words(section) == spoken


@pytest.mark.parametrize(
    "year,spoken",
    [
        (2019, "twenty nineteen"),
        (2020, "twenty twenty"),
        (2021, "twenty twenty-one"),
        (2005, "two thousand five"),
        (2000, "two thousand"),
        (1999, "nineteen ninety-nine"),
    ],
)
def test_year_to_words(year: int, spoken: str) -> None:
    assert year_to_words(year) == spoken


@pytest.mark.parametrize(
    "n,word",
    [
        (0, "zero"),
        (7, "seven"),
        (13, "thirteen"),
        (37, "thirty-seven"),
        (100, "one hundred"),
        (123, "one hundred twenty-three"),
        (2019, "two thousand nineteen"),
        (2020, "two thousand twenty"),
        (1_000_000, "one million"),
    ],
)
def test_int_to_words(n: int, word: str) -> None:
    assert int_to_words(n) == word


@pytest.mark.parametrize(
    "token,word",
    [
        ("5.2", "five point two"),
        ("0.05", "zero point zero five"),
        ("-3", "minus three"),
        ("1,000", "one thousand"),
        ("37", "thirty-seven"),
    ],
)
def test_number_to_words(token: str, word: str) -> None:
    assert number_to_words(token) == word


@pytest.mark.parametrize(
    "raw,spoken",
    [
        ("37%", "thirty-seven percent"),
        ("10^-3", "ten to the minus three"),
        ("R^2", "R squared"),
        ("x^3", "x cubed"),
        ("0.3-0.5", "zero point three to zero point five"),
        ("2-8", "two to eight"),
        ("-20 to -30", "minus twenty to minus thirty"),
    ],
)
def test_normalize_numbers(raw: str, spoken: str) -> None:
    assert normalize_numbers(raw) == spoken


def test_sentence_period_after_number_survives() -> None:
    assert normalize_numbers("year 2019. Next") == "year two thousand nineteen. Next"


def test_comma_after_number_survives() -> None:
    assert normalize_numbers("Figure 1, then") == "Figure one, then"
