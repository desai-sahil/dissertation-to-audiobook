from __future__ import annotations

from thesis_audiobook.lexicon import DEFAULT_LEXICON, apply_lexicon


def test_compound_grapheme_wins_over_substrings() -> None:
    assert (
        apply_lexicon("PYR-PP2C-OST1-SLAC1", DEFAULT_LEXICON)
        == "P Y R, P P two C, O S T one, slac one"
    )


def test_gene_pronunciation() -> None:
    assert apply_lexicon("GhSLAC1", DEFAULT_LEXICON) == "G H slac one"
    assert apply_lexicon("slac1", DEFAULT_LEXICON) == "slac one"
    assert apply_lexicon("osca1", DEFAULT_LEXICON) == "osca one"


def test_word_boundary_respected() -> None:
    # "gs" must not fire inside "things".
    assert apply_lexicon("things", DEFAULT_LEXICON) == "things"


def test_symbol_expansion() -> None:
    assert apply_lexicon("gs", DEFAULT_LEXICON) == "stomatal conductance"
