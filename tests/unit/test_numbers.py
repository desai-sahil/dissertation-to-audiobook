from __future__ import annotations

import pytest

from thesis_audiobook.normalization.numbers import (
    int_to_words,
    normalize_numbers,
    number_to_words,
    section_to_words,
    spell_numbers,
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
    "text,spoken",
    [
        ("the 1890s", "the eighteen nineties"),
        ("the 1960s", "the nineteen sixties"),
        ("the 2010s", "the twenty tens"),
        ("the 1900s", "the nineteen hundreds"),
        ("the 2000s", "the two thousands"),
    ],
)
def test_decades(text: str, spoken: str) -> None:
    assert normalize_numbers(text) == spoken


@pytest.mark.parametrize(
    "text,spoken",
    [
        # the bug: the generic decimal pass split 2.2.4 and left a stray ".four"
        ("see Section 2.2.4 here", "see Section two point two point four here"),
        ("in Equation 1.4", "in Equation one point four"),
        ("Figure 3.6 shows", "Figure three point six shows"),
        ("per Eq. 6.11", "per Eq. six point eleven"),
        # an ordinary decimal (not a cross-ref) is left to the normal cardinal path
        ("a value of 0.4 MPa", "a value of zero point four MPa"),
    ],
)
def test_cross_references(text: str, spoken: str) -> None:
    assert normalize_numbers(text) == spoken


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


def test_alphanumeric_code_read_digit_by_digit() -> None:
    # A part/model/serial code (digits, a letter, then more digits) is read digit by digit, never
    # as a cardinal "nine thousand..." (QC found "No.9657K286" -> "nine thousand six hundred...").
    out = " ".join(spell_numbers("Part No.9657K286 here").split())
    assert out == "Part No. nine six five seven K two eight six here"
    assert "thousand" not in out
    # SAFETY: a plain quantity glued to a unit is still a cardinal, not digit-by-digit
    assert " ".join(spell_numbers("used 56mM buffer").split()) == "used fifty-six mM buffer"
    assert " ".join(spell_numbers("model 3B+ board").split()) == "model three B+ board"


def test_nxm_dimensions_read_as_times() -> None:
    # an ASCII "x" between two numbers is a dimension/multiplication, not a code or a glued unit:
    # read it as "times" (review-found: the part-code rule was spelling "512x512" digit-by-digit;
    # "times" is also correct for scientific notation like "2.3x10"). Each operand is then spelled
    # normally, so a decimal stays "one point five", never "one.five".
    assert spell_numbers("imaged at 100x100 resolution") == (
        "imaged at one hundred times one hundred resolution"
    )
    assert spell_numbers("the 1.5x3 devices") == "the one point five times three devices"
    # the alphanumeric part-code rule still applies (no "x" between the digits)
    assert (
        " ".join(spell_numbers("No.9657K286").split()) == "No. nine six five seven K two eight six"
    )
