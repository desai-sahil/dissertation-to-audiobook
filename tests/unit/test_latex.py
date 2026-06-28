from __future__ import annotations

import pytest

from thesis_audiobook.normalization.latex import clean_markup, split_display_math


def test_split_display_math_extracts_inner_latex() -> None:
    assert split_display_math(r"$$\psi = \frac{RT}{v} \ln(x) \tag{1.1}$$") == (
        r"\psi = \frac{RT}{v} \ln(x) \tag{1.1}"
    )
    assert split_display_math("not an equation") is None
    assert split_display_math(r"text with $inline$ math") is None


def test_split_display_math_folds_trailing_number_on_its_own_line() -> None:
    # Marker renders a numbered display equation as `$$...$$` then `(X.Y)` on the next line;
    # the number is folded into a \tag so the math stage can announce it.
    assert split_display_math("$$VPD = \\frac{P_{sat}(T)}{100\\%}$$\n (1.4)") == (
        r"VPD = \frac{P_{sat}(T)}{100\%} \tag{1.4}"
    )
    # also when the number sits right after the closing $$ on the same line
    assert split_display_math(r"$$e_f = \sqrt{x}$$ (2.5)") == r"e_f = \sqrt{x} \tag{2.5}"
    # an unnumbered display equation (an intermediate step) returns its body, no tag
    assert split_display_math(r"$$a = b + c$$") == "a = b + c"
    # a bare parenthetical that is not an equation number (no decimal) is not folded
    assert split_display_math(r"$$a = b$$ (note)") is None


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


def test_clean_markup_drops_sentence_end_citation_superscript() -> None:
    # A superscript AFTER a sentence period is a citation marker, not a decimal: drop the number
    # (QC found "xylem.<sup>31</sup>" was becoming "xylem.thirty-one"). A digit before the period
    # still marks a Marker-split decimal and is kept.
    assert clean_markup("through the xylem.<sup>31</sup> When subjected") == (
        "through the xylem. When subjected"
    )
    assert clean_markup("boiling.<sup>31, 32</sup> The principle") == "boiling. The principle"
    assert clean_markup("constant 8.<sup>314</sup> J") == "constant 8.314 J"  # decimal still kept


def test_clean_markup_drops_clause_punctuation_citation_superscript() -> None:
    # A numeric superscript after a clause-ending ')', ']', ':', ';', ',' (or a space-separated
    # period) is a citation marker, not a value: drop it. QC found "(Ψs)48", "sand,33",
    # "References. 17, 56", and "SPC).17" all leaking footnote numbers into the audio.
    assert clean_markup("the term (Ψs)<sup>48</sup> governs") == "the term (Ψs) governs"
    assert clean_markup("dry sand,<sup>33</sup> which holds") == "dry sand, which holds"
    assert clean_markup("see References. <sup>17, 56</sup> for") == "see References. for"
    # a period after a non-digit (here ")") ends a clause, so its superscript is a citation marker
    assert clean_markup("the SPC).<sup>17</sup> system") == "the SPC). system"
    # SAFETY: a standalone shredded-equation digit after an operator is a real value, kept
    assert "= 0 Pa" in clean_markup("ψ <sup>=</sup> <sup>0</sup> Pa")


def test_clean_markup_drops_reference_pointer_citation() -> None:
    # "based on References <sup>N</sup>" / "according to Ref.<sup>N</sup>" is a citation pointer:
    # the lead-in + the word + the superscript are machinery and read as nothing. Drop the whole
    # span to a sentence period instead of leaking a dangling "based on References." (QC found it).
    assert clean_markup("ranges based on References. <sup>17.56</sup> Importantly the") == (
        "ranges. Importantly the"
    )
    assert clean_markup("the model (tuned based on References<sup>17,56</sup>) here") == (
        "the model (tuned.) here"
    )
    assert clean_markup("value according to Ref.<sup>4</sup> rises") == "value. rises"


def test_clean_markup_embedded_display_and_greek_spacing() -> None:
    assert "delta psi" in clean_markup(r"gradient $\Delta\psi$ here")  # not "deltapsi"
    out = clean_markup(r"see $$\psi = \frac{RT}{v}$$ inline")  # $$ embedded mid-paragraph
    assert "$" not in out and "psi" in out and "RT over v" in out


def test_clean_markup_strips_markdown_emphasis() -> None:
    # markdown bold/italic must not be voiced as "asterisk"
    assert clean_markup("**BIOGRAPHICAL SKETCH**") == "BIOGRAPHICAL SKETCH"
    assert clean_markup("the *adsorption-tension* activity") == "the adsorption-tension activity"
    assert clean_markup("variable $*v*$ here").count("*") == 0
    assert "*" not in clean_markup("a * stray * marker")  # leftover markers dropped, not voiced


def test_clean_markup_reassembled_entity_from_marker_superscript() -> None:
    # Marker mangles ">" as "<sup>&</sup>gt;"; the sup handler reassembles "&gt;", which the
    # entity pass (run AFTER sup/sub) must then convert. Was leaking "&gt;" into the audio.
    assert "greater than" in clean_markup("(I/I) *<sup>i</sup>* <sup>&</sup>gt; <sup>0</sup>")
    assert "&" not in clean_markup("x <sup>&</sup>gt; y")


def test_clean_markup_html_entities_and_inverted_marks() -> None:
    assert clean_markup("a &gt; b and c &lt; d") == "a greater than b and c less than d"
    assert (
        clean_markup("curing time ¡ twenty-four hours") == "curing time less than twenty-four hours"
    )
    assert clean_markup("excluded if ¿ ten nm") == "excluded if greater than ten nm"


def test_clean_markup_matrix_and_nested_frac() -> None:
    out = clean_markup(r"$\begin{bmatrix} a & b \end{bmatrix}$")
    assert "bmatrix" not in out and "&" not in out and "\\" not in out
    # nested \frac is handled, not leaked as the word "frac"
    nested = clean_markup(r"$\frac{a_{x}}{b}$")
    assert "frac" not in nested and "over" in nested


def test_clean_markup_shredded_superscript_equation() -> None:
    # Marker typesets some equations with every character in its own <sup>; a digit superscript
    # preceded by a space/operator is a real value, not a citation marker, and must be KEPT.
    # (QC found "8.314" -> ".314", "= 0 Pa" -> "= Pa", "2.88 ml" -> "squared.eighty-eight".)
    gas = clean_markup("where <sup>R</sup> <sup>=</sup> <sup>8</sup>.<sup>314</sup> J")
    assert "8.314" in gas and "R = 8.314 J" in gas
    assert "0 Pa" in clean_markup("ψ <sup>=</sup> <sup>0</sup> Pa")  # the zero is not dropped
    assert "< 0" in clean_markup("water cannot have ψ < <sup>0</sup>, as")
    assert "2.88 ml" in clean_markup("and <sup>2</sup>.<sup>88</sup> ml Brij")  # not "squared"
    assert "0.45" in clean_markup("porosity, ϕ <sup>=</sup> <sup>0</sup>.<sup>45</sup> and")


def test_clean_markup_unicode_math_glyphs() -> None:
    # Literal unicode glyphs Marker OCRs into prose (not inside $...$) must become spoken words.
    assert "much less than" in clean_markup("ψ term <sup>≪</sup> ψ TLP")
    assert clean_markup("x ≡ y") == "x defined as y"
    assert clean_markup("at ∼ 3 nm") == "at approximately 3 nm"
    assert clean_markup("700 ◦C") == "700 degrees C"
    assert "delta" in clean_markup("the gradient ∆I is") and "∆" not in clean_markup("∆I")
    assert "−" not in clean_markup("a − b") and "minus" in clean_markup("a − b")


def test_clean_markup_times_between_numbers() -> None:
    # The italic *x* Marker glues as "1.804x10" must read as multiplication, not garble the
    # number (was "one.eight hundred four x one zero" after normalization).
    assert clean_markup("v = 1.804*x*10<sup>5</sup>") == "v = 1.804 times 10 to the power of 5"
    assert clean_markup("about 4.2 x 10<sup>3</sup>") == "about 4.2 times 10 to the power of 3"
    # an "x" not flanked by two digits is left alone (variable / magnification)
    assert "times" not in clean_markup("the 10x* objective")  # digit-x-space, not digit-x-digit


def test_clean_markup_superscript_degree() -> None:
    assert clean_markup("at 40<sup>o</sup>C here") == "at 40 degrees C here"
    assert clean_markup("at 25<sup>o</sup>C") == "at 25 degrees C"


def test_clean_markup_chemical_formula_superscripts() -> None:
    # Marker mis-typesets CO2 etc. with a superscript; read as the formula, not "CO squared".
    assert clean_markup("the CO<sup>2</sup> rate") == "the CO2 rate"
    assert clean_markup("flux of O<sup>2</sup>") == "flux of O2"
    assert clean_markup("a drop of H<sup>2</sup>O here") == "a drop of H2O here"
    assert clean_markup("rinsed in HgCl<sup>2</sup> then") == "rinsed in HgCl2 then"
    # C3/C4 are plant types, not exponents
    assert clean_markup("the C<sup>3</sup> and C<sup>4</sup> plants") == "the C3 and C4 plants"
    # H2O shredded across superscripts (the G^{H2O} conductance) is reassembled, not "degrees"
    out = clean_markup("conductance (G<sup>H</sup>2<sup>O</sup>) rose")
    assert "H2O" in out and "degrees" not in out
    # a genuine unit exponent is still spoken as squared/cubed
    assert clean_markup("area m<sup>2</sup> wide") == "area m squared wide"
    assert "cubed" in clean_markup("volume cm<sup>3</sup>")


def test_clean_markup_latex_subscript_is_not_squared() -> None:
    # A LaTeX subscript "_2" is a subscript, not an exponent: "$CO_2$" must not read "CO squared".
    assert "squared" not in clean_markup("the $CO_2$ level")
    assert "CO2" in clean_markup("the $CO_2$ level")
    assert clean_markup("the $v_w$ term") == "the v w term"  # subscript letter keeps its space
    # a real exponent in math is still squared
    assert "squared" in clean_markup("area $m^2$ here")


def test_clean_markup_never_leaks_latex_or_tags() -> None:
    messy = r"$E=4.2\times10^{-5}~{\rm kg/(m^2.s)}$ and $\mu m$ scale<sup>3</sup>"
    out = clean_markup(messy)
    assert "$" not in out and "\\" not in out and "<" not in out
    assert "times" in out and "mu m" in out
