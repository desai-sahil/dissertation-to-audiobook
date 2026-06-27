from __future__ import annotations

import pytest

from thesis_audiobook.normalization.latex import clean_markup, split_display_math


def test_split_display_math_extracts_inner_latex() -> None:
    assert split_display_math(r"$$\psi = \frac{RT}{v} \ln(x) \tag{1.1}$$") == (
        r"\psi = \frac{RT}{v} \ln(x) \tag{1.1}"
    )
    assert split_display_math("not an equation") is None
    assert split_display_math(r"text with $inline$ math") is None


def test_clean_markup_noop_on_plain_prose() -> None:
    plain = "The stomata regulate transpiration under drought stress."
    assert clean_markup(plain) == plain


@pytest.mark.parametrize(
    "raw,expected_contains",
    [
        (r"the value $\psi$ matters", "psi"),
        (r"stomatal conductance $g_s$ rose", "g s"),
        (r"water potential $\psi_{xyl}$ fell", "psi xyl"),
        (r"area $m^2$ here", "m squared"),
        (r"$VPD_{leaf}$ increased", "VPD leaf"),
        (r"$a \leq b$", "less than or equal to"),
        (r"$\psi_{50\%}$", "percent"),
    ],
)
def test_clean_markup_inline_math(raw: str, expected_contains: str) -> None:
    out = clean_markup(raw)
    assert expected_contains in out
    assert "$" not in out and "\\" not in out and "{" not in out


def test_clean_markup_html() -> None:
    assert clean_markup("area m<sup>2</sup> wide") == "area m squared wide"
    assert clean_markup("line one<br>line two") == "line one line two"
    # bare-number superscripts AFTER A WORD (citation markers) are dropped, not voiced
    assert clean_markup("as shown<sup>12</sup> here") == "as shown here"
    assert "<sub>" not in clean_markup("x<sub>i</sub>") and "x i" in clean_markup("x<sub>i</sub>")
    assert clean_markup("<b>bold</b> text") == "bold text"


def test_clean_markup_number_superscripts_are_kept() -> None:
    # A superscript attached to a NUMBER is a value, not a citation - keep it (QC found
    # "8.314" was becoming "8." and "10^5" was becoming "10").
    assert clean_markup("R = 8.<sup>314</sup> J") == "R = 8.314 J"
    assert clean_markup("about -10<sup>5</sup> Pa") == "about -10 to the power of 5 Pa"
    assert clean_markup("10<sup>2</sup> to 10<sup>6</sup>") == (
        "10 to the power of 2 to 10 to the power of 6"
    )


def test_clean_markup_embedded_display_and_greek_spacing() -> None:
    assert "delta psi" in clean_markup(r"gradient $\Delta\psi$ here")  # not "deltapsi"
    out = clean_markup(r"see $$\psi = \frac{RT}{v}$$ inline")  # $$ embedded mid-paragraph
    assert "$" not in out and "psi" in out and "RT over v" in out


def test_clean_markup_never_leaks_latex_or_tags() -> None:
    messy = r"$E=4.2\times10^{-5}~{\rm kg/(m^2.s)}$ and $\mu m$ scale<sup>3</sup>"
    out = clean_markup(messy)
    assert "$" not in out and "\\" not in out and "<" not in out
    assert "times" in out and "mu m" in out
