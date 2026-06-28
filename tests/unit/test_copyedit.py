from __future__ import annotations

import pytest

from thesis_audiobook.copyedit import copyedit_guard


@pytest.mark.parametrize(
    "find,replace",
    [
        ("responce", "response"),  # spelling typo (one content-word substitution)
        ("the stomotal pore", "the stomatal pore"),
        ("photosythetically active", "photosynthetically active"),
        ("in cell wall", "in the cell wall"),  # grammar: insert an article (function word)
        ("the datas show", "the data show"),  # agreement (one content sub)
        ("the effect are", "the effect is"),  # copula agreement (function words only)
        ("withincreasing light", "with increasing light"),  # fusion split (function-word half)
        ("datashow a trend", "data show a trend"),  # fusion split, BOTH halves content
        ("waterstress lowered it", "water stress lowered it"),  # fusion split, both content
        ("overview:one)", "overview: one)"),  # spacing only
        ("at 5 mm thick", "at 5 mm thick "),  # whitespace only, number untouched
    ],
)
def test_copyedit_guard_allows_meaning_preserving(find: str, replace: str) -> None:
    assert copyedit_guard(find, replace)


@pytest.mark.parametrize(
    "find,replace",
    [
        ("photosynthesis increased with light", "photosynthesis decreased with light"),  # flip
        ("values stayed above the threshold", "values stayed below the threshold"),  # above/below
        ("a higher rate", "a lower rate"),
        ("a positive correlation", "a negative correlation"),  # sign of a result
        ("the rate rose sharply", "the rate fell sharply"),
        ("the water potential psi declined", "the water potential phi declined"),  # Greek swap
        ("alpha was measured", "beta was measured"),
        ("the area in meters squared", "the area in meters cubed"),  # exponent
        ("twelve grams per liter", "twelve grams times liter"),  # per -> times
        ("thousands of cells", "millions of cells"),  # magnitude
    ],
)
def test_copyedit_guard_blocks_claim_and_value_flips(find: str, replace: str) -> None:
    assert not copyedit_guard(find, replace)


@pytest.mark.parametrize(
    "find,replace",
    [
        ("was 0.15 MPa", "was 0.5 MPa"),  # number changed -> blocked
        ("rose to 5 units", "rose to 9 units"),  # number changed
        ("is not significant", "is significant"),  # negation dropped -> claim flipped
        ("the effect held", "the effect did not hold"),  # negation added
        ("the effect", "the significant effect"),  # content word inserted (a hedge)
        ("only the leaf rose", "the leaf rose"),  # scope word dropped
        ("more than expected", "less than expected"),  # scope word swapped (polarity)
        ("rose to five units", "rose to nine units"),  # spelled-out number changed
        ("at two point five MPa", "at five point two MPa"),  # spelled-out number reordered
        ("five hundred samples", "five thousand samples"),  # scale word changed
        ("at five millimeters depth", "at five centimeters depth"),  # unit swapped
        ("the rate increased here", "the rate increased a lot here over time"),  # paraphrase
        ("", "x"),  # empty find
        ("same", "same"),  # no-op
    ],
)
def test_copyedit_guard_blocks_meaning_changes(find: str, replace: str) -> None:
    assert not copyedit_guard(find, replace)


def test_copyedit_guard_allows_single_content_substitution_only() -> None:
    # exactly one content-word substitution is allowed (a typo); two is a paraphrase -> blocked
    assert copyedit_guard("the responce curve", "the response curve")
    assert not copyedit_guard("the responce curv", "the response curve here")


def test_copyedit_guard_rejects_overlong_span() -> None:
    long = "word " * 60  # > COPYEDIT_MAX_SPAN characters
    assert not copyedit_guard(long, long + "x")
