"""Phase-1 read-aloud anomaly fixes (deterministic, parser-agnostic)."""

from __future__ import annotations

from thesis_audiobook.lexicon import DEFAULT_LEXICON
from thesis_audiobook.normalization import _collapse_redundant_parenthetical, normalize_all


def test_collapse_drops_duplicate_parenthetical() -> None:
    assert (
        _collapse_redundant_parenthetical("abscisic acid (abscisic acid) synthesis")
        == "abscisic acid synthesis"
    )
    # hyphen-vs-space variant collapses too
    assert (
        _collapse_redundant_parenthetical("large outside-xylem (outside xylem) resistance")
        == "large outside-xylem resistance"
    )
    assert (
        _collapse_redundant_parenthetical(
            "soil-plant-atmosphere continuum (soil plant atmosphere continuum) model"
        )
        == "soil-plant-atmosphere continuum model"
    )


def test_collapse_keeps_real_glosses_and_acronym_intros() -> None:
    # An acronym intro is NOT a duplicate: the inside is not a suffix of the phrase.
    assert (
        _collapse_redundant_parenthetical("abscisic acid (A B A) signaling")
        == "abscisic acid (A B A) signaling"
    )
    assert (
        _collapse_redundant_parenthetical("the OnGuard platform (Blatt and colleagues)")
        == "the OnGuard platform (Blatt and colleagues)"
    )


def test_collapse_runs_inside_normalize_all() -> None:
    out = normalize_all("vapor pressure deficit (vapor pressure deficit) rose", DEFAULT_LEXICON)
    assert "vapor pressure deficit (vapor pressure deficit)" not in out
    assert out.count("vapor pressure deficit") == 1


def test_collapse_is_idempotent_and_keeps_single_word() -> None:
    for raw in ["a_(a)", "foo (foo) (foo)", "x (x) (x) (x)"]:
        once = normalize_all(raw, DEFAULT_LEXICON)
        assert normalize_all(once, DEFAULT_LEXICON) == once  # idempotent
    # A chained multi-word duplicate fully collapses in one call.
    chain = normalize_all(
        "vapor pressure deficit (vapor pressure deficit) (vapor pressure deficit) rose",
        DEFAULT_LEXICON,
    )
    assert chain.count("vapor pressure deficit") == 1
    # A lone repeated word is a real (terse) gloss, not a duplicate, so it is kept.
    assert "(conductance)" in normalize_all(
        "stomatal conductance (conductance) rose", DEFAULT_LEXICON
    )


def test_url_ignores_filenames_and_preserves_punctuation() -> None:
    assert "the link in the text" not in normalize_all(
        "saved as results.csv/sheet1", DEFAULT_LEXICON
    )
    assert normalize_all("visit http://example.com/path. Next.", DEFAULT_LEXICON).endswith("Next.")
    assert "(" in normalize_all("see (http://a.io/x) end", DEFAULT_LEXICON)


def test_pdf_split_url_collapses_to_one_link_phrase() -> None:
    # poppler split the protocol off; the domain/path remnant + trailing slash must not
    # read as "...over...over". Both fragments collapse to one "the link in the text".
    out = normalize_all(
        "available at https://desai-sahil. github.io/stomatal-conductance-model/ today",
        DEFAULT_LEXICON,
    )
    assert "over" not in out
    assert "github" not in out
    assert out.count("the link in the text") == 1
