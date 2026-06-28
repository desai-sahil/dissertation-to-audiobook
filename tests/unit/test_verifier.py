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
