from __future__ import annotations

import pytest

from thesis_audiobook.citation_naturalize import (
    GENERIC_PHRASES,
    apply_genericization,
    build_genericize_prompt,
    capitalized_citation_strips,
    find_narrative_mentions,
    naturalize_citations,
    parse_genericization,
    strip_markers,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("as shown in [12] and [3, 4] here", "as shown in and here"),  # bracketed dropped
        ("the dynamics.41 of uptake", "the dynamics. of uptake"),  # bare fused number dropped
        ("metastable state.18, 19 occurs", "metastable state. occurs"),
        ("susceptibility to diseases.10–16 here", "susceptibility to diseases. here"),  # range
        # a capital word fused to a COMMA list is a citation -> stripped
        ("from the Stroock Group.20, 21 we", "from the Stroock Group. we"),
        ("metastable State.18, 19 here", "metastable State. here"),
        # a capital word fused to a SINGLE number is ambiguous (code/cultivar/part) -> left intact
        ("rootstock Bud.118 was grafted", "rootstock Bud.118 was grafted"),
        ("pump KNF.300 ran", "pump KNF.300 ran"),
        ("see Group.20 alone", "see Group.20 alone"),
        # SAFETY (review-found): a capital word fused to a dash RANGE is a code/catalog/cross, KEPT
        ("antibody Lot.118-22 was", "antibody Lot.118-22 was"),
        ("reagents Cat.13-45 from", "reagents Cat.13-45 from"),
        ("the cross Bud.118-490 here", "the cross Bud.118-490 here"),
        # a LOWERCASE content word is still stripped for any number form (single, comma, dash)
        ("diseases.10-16 here", "diseases. here"),
        # a COMMA-fused citation list (no space after the comma) is stripped, comma dropped
        ("the Stroock group,20, 21 for", "the Stroock group for"),
        ("the micro-tensiometer,20, 21 here", "the micro-tensiometer here"),
        # SAFETY: real "word, NUMBER" (space after comma) and a single fused cross-ref are kept
        ("we measured group, 20 samples", "we measured group, 20 samples"),
        ("see Table,2 here", "see Table,2 here"),
        # a part number / alphanumeric code is NOT a citation and must be left intact
        ("the spring (Part No.9657K286) was", "the spring (Part No.9657K286) was"),
        (
            "we refer to Pagay et al.,21 and Black et al.,20",
            "we refer to Pagay et al. and Black et al.",
        ),
        ("driven by ABA (Geiger et al., 2009; Brandt et al., 2012).", "driven by ABA."),
        # SAFETY: a real decimal and a real sentence-then-number must be untouched
        ("a value of 0.4 MPa", "a value of 0.4 MPa"),
        ("growth. 41 plants were grown", "growth. 41 plants were grown"),
        # SAFETY (review-found, high): initials / abbreviations / labels keep their number
        ("were on M.26 semi-dwarfing rootstock", "were on M.26 semi-dwarfing rootstock"),
        ("nighttime irrigation No.1 as seen", "nighttime irrigation No.1 as seen"),
        ("see Fig.3 for details", "see Fig.3 for details"),
        ("shown in Figure E.11, E.12 with", "shown in Figure E.11, E.12 with"),
        ("the spring (Part No.9657K286) was", "the spring (Part No.9657K286) was"),
        # SAFETY (review-found, high): a parenthetical that is a date/value, not a citation, is kept
        ("used in Summer 2020 here", "used in Summer 2020 here"),
        ("the cells (n = 2020) were counted", "the cells (n = 2020) were counted"),
        (
            "measured (20 July 2018, 1500-1700 hrs) at the farm",
            "measured (20 July 2018, 1500-1700 hrs) at the farm",
        ),
        # but a real author-year parenthetical IS dropped
        ("driven by ABA (Buckley and Mott, 2013) here", "driven by ABA here"),
    ],
)
def test_strip_markers(text: str, expected: str) -> None:
    assert strip_markers(text) == expected


def test_capitalized_citation_strips_surfaces_only_comma_lists() -> None:
    # the stage warns on these (a comma list after a capital word is usually a citation, but could
    # be a code series like "Bud.9, 62, 118"); dash ranges and single numbers are not flagged
    spans = capitalized_citation_strips("Stroock Group.20, 21 and Bud.118-490 and Bud.9, 62, 118")
    assert spans == ["Group.20, 21", "Bud.9, 62, 118"]
    assert capitalized_citation_strips("Bud.118 and Cat.13-45 and dynamics.41, 42") == []
    # a capital comma-fused cross-ref list is surfaced too; a lowercase citation is not warned
    assert capitalized_citation_strips("see Table,2, 3 but group,20, 21") == ["Table,2, 3"]


def test_find_narrative_mentions_only_et_al() -> None:
    # anchored on "et al." (the source form); a bare "X and others" common-noun phrase is NOT a
    # mention (avoids genericizing "Apples and others were tested").
    text = "Chalmer et al. note that, while Apples and others were tested, as do Chalmer et al."
    assert find_narrative_mentions(text) == ["Chalmer et al."]  # deduped, no false positive


def test_dangling_lead_in_is_removed_after_stripping() -> None:
    assert strip_markers("the effect was clear as shown in [12].") == "the effect was clear."
    # a real "according to X" with content after it is untouched (only orphaned lead-ins go)
    assert strip_markers("according to the data, X held") == "according to the data, X held"


def test_parse_genericization_only_allows_fixed_phrases() -> None:
    raw = '{"Chalmer et al.": "researchers", "Smith et al.": "according to my own analysis"}'
    out = parse_genericization(raw)
    assert out == {"Chalmer et al.": "researchers"}  # free-text phrase rejected
    assert all(v in GENERIC_PHRASES for v in out.values())
    assert parse_genericization("not json") == {}  # offline mock -> no genericizing


def test_apply_genericization_whole_span() -> None:
    text = "Chalmer et al. note that water deficit helps"
    out = apply_genericization(text, {"Chalmer et al.": "researchers"})
    assert out == "researchers note that water deficit helps"


def test_naturalize_offline_degrades_to_and_others() -> None:
    # no mapping (offline) -> markers stripped, narrative mention reads naturally
    assert naturalize_citations("Chalmer et al. note that.41 here") == (
        "Chalmer and others note that. here"
    )


def test_naturalize_with_mapping_genericizes() -> None:
    out = naturalize_citations("Chalmer et al. note that X", {"Chalmer et al.": "researchers"})
    assert out == "researchers note that X"


def test_citation_list_collapses_to_one_phrase() -> None:
    # a list of genericized citations runs together; collapse to a single "several studies"
    out = naturalize_citations(
        "we refer to Pagay et al.,21 Black et al.,20 and Zhu.",
        {"Pagay et al.": "prior studies", "Black et al.": "several studies"},
    )
    assert out == "we refer to several studies"
    # a single genericized mention is NOT collapsed, and a following sentence subject is safe
    assert (
        naturalize_citations("researchers, Stomata regulate transpiration.", {"X et al.": "x"})
        == "researchers, Stomata regulate transpiration."
    )


def test_prompt_lists_only_allowed_phrases() -> None:
    prompt = build_genericize_prompt(["Chalmer et al."])
    assert "Chalmer et al." in prompt and "researchers" in prompt
