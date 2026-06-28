from __future__ import annotations

from thesis_audiobook.verifier import verify_segment


def _kinds(source: str, spoken: str) -> set[str]:
    return {v.kind for v in verify_segment(source, spoken).violations}


# --- the happy path: a constrained, faithful rewrite passes the whole floor ---


def test_faithful_rewrite_passes() -> None:
    source = (
        "Conductance decreased by 0.5 units when potential fell below -2.0 MPa "
        "(Smith et al., 2019)."
    )
    spoken = (
        "Conductance decreased by zero point five units when potential fell below "
        "minus two point zero megapascals."
    )
    verdict = verify_segment(source, spoken)
    assert verdict.ok, verdict.violations


def test_close_paraphrase_with_added_function_words_passes() -> None:
    verdict = verify_segment(
        "cells imaged at resolution", "the cells were imaged at high resolution"
    )
    assert verdict.ok, verdict.violations


# --- values ---


def test_changed_decimal_value_is_caught() -> None:
    v = verify_segment("increased by 0.5 units", "increased by zero point nine units")
    assert not v.ok
    assert v.violations[0].kind == "values" and "missing" in v.violations[0].detail


def test_dropped_value_is_caught() -> None:
    assert _kinds("held at 0.5 units", "held at the units") == {"values"}


def test_percentage_value_preserved_passes() -> None:
    assert verify_segment("rose 37% overall", "rose thirty-seven percent overall").ok


def test_value_reordering_is_caught() -> None:
    v = verify_segment("0.5 then 0.9 later", "zero point nine then zero point five later")
    assert not v.ok
    assert any(viol.kind == "values" and "out of order" in viol.detail for viol in v.violations)


def test_hyphenated_range_is_two_values_not_a_negative() -> None:
    # "2.2-2.4" is a range (e.g. a figure range), not the negative "-2.4"; both operands voiced.
    assert verify_segment(
        "see Figures 2.2-2.4 and the 0.3-0.5 band",
        "see Figures two point two through two point four and the zero point three "
        "to zero point five band",
    ).ok


def test_cross_reference_numbers_are_not_required_values() -> None:
    # a decimal after Figure/Eq/Table/Section is a pointer, not a measurement: dropping it is fine.
    assert verify_segment("As shown in Figure 2.1, the trend holds.", "the trend holds.").ok
    assert verify_segment("Equation 3.4 gives the result.", "An equation gives the result.").ok


def test_lone_parenthesized_decimal_is_an_equation_number() -> None:
    # "(2.15)" alone in parens is an equation/figure number, not a measurement.
    assert verify_segment("the relation (2.15) follows from above", "the relation follows").ok
    # but a parenthesized value WITH a unit is still a measurement that must survive
    assert not verify_segment("the pressure (0.5 MPa) held", "the pressure held").ok


def test_real_negative_decimal_still_checked() -> None:
    # a genuine negative (after a space) keeps its sign and must survive.
    assert not verify_segment("a delta of -2.4 units", "a delta of two units").ok
    assert verify_segment("a delta of -2.4 units", "a delta of negative two point four units").ok


def test_dropped_citation_year_is_not_a_value_violation() -> None:
    # bare integers (citation years, ref numbers, pages) are out of scope by design - a faithful
    # rewrite drops "(Smith et al., 2019; Jones 2021)" and must NOT be flagged for losing 2019/2021.
    assert verify_segment(
        "as shown before (Smith et al., 2019; Jones 2021).", "as shown before."
    ).ok


# --- polarity / direction ---


def test_dropped_negation_is_caught() -> None:
    assert _kinds("the change was not significant", "the change was significant") == {"polarity"}


def test_direction_flip_is_caught() -> None:
    assert _kinds("expression increased in mutants", "expression decreased in mutants") == {
        "direction"
    }


def test_direction_synonym_passes() -> None:
    # higher -> greater is the same direction (up); a faithful rewrite, not a flip.
    assert verify_segment("the signal was higher", "the signal was greater").ok


def test_total_loss_of_direction_is_caught() -> None:
    assert _kinds("expression increased in mutants", "expression changed in mutants") == {
        "direction"
    }


def test_voicing_a_symbol_into_direction_or_scope_passes() -> None:
    # the narrator voices "< 0" as "negative" and "<" as "less than": ADDING direction/scope words
    # is allowed (it is the narrator's job); only drops/flips are violations.
    assert verify_segment(
        "the change was significant at p < 0.05",
        "the change was significant at p less than zero point zero five",
    ).ok
    assert verify_segment(
        "the slope delta was -2.0", "the slope delta was negative two point zero"
    ).ok


def test_dropped_scope_word_is_caught() -> None:
    assert _kinds("only the mutant responded", "the mutant responded") == {"polarity"}


def test_added_negation_is_caught() -> None:
    # voicing never introduces a "not"; adding one flips the claim, so it is flagged.
    assert _kinds("the effect was significant", "the effect was not significant") == {"polarity"}


# --- speakable allowlist ---


def test_unspeakable_characters_are_caught() -> None:
    v = verify_segment("the value rose", "the value rose by 5% +/- 2")
    assert not v.ok
    detail = next(viol.detail for viol in v.violations if viol.kind == "speakable")
    assert "5" in detail and "%" in detail  # a residual digit and a raw percent sign both trip it


def test_clean_spoken_text_is_speakable() -> None:
    assert verify_segment("ok", "perfectly ordinary spoken prose, with punctuation.").ok


# --- paraphrase ---


def test_wholesale_injection_is_caught() -> None:
    spoken = (
        "cells were imaged using completely different elaborate proprietary fluorescence "
        "confocal apparatus"
    )
    assert _kinds("cells were imaged", spoken) == {"paraphrase"}


# --- composition: a verdict collects every violated invariant ---


def test_multiple_violations_are_all_reported() -> None:
    v = verify_segment(
        "increased by 0.5",
        "decreased by zero point nine and many novel injected fabricated extra surprising clauses",
    )
    kinds = {viol.kind for viol in v.violations}
    assert {"values", "direction"} <= kinds
    assert not v.ok
