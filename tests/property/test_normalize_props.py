from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from thesis_audiobook.lexicon import DEFAULT_LEXICON
from thesis_audiobook.normalization import FORBIDDEN_RAW_TOKENS, normalize_all

L = DEFAULT_LEXICON


@given(st.text(max_size=200))
def test_normalizer_is_idempotent(text: str) -> None:
    once = normalize_all(text, L)
    assert normalize_all(once, L) == once


@given(st.text(alphabet="ab ()-_.", max_size=40))
def test_normalizer_is_idempotent_on_paren_dense_text(text: str) -> None:
    # A focused alphabet that actually produces "word (word)" adjacency, underscores, and
    # chained parentheticals - the redundant-parenthetical patterns the broad-alphabet
    # strategy above almost never generates.
    once = normalize_all(text, L)
    assert normalize_all(once, L) == once


@given(st.text(max_size=200))
def test_no_raw_notation_leaks(text: str) -> None:
    out = normalize_all(text, L)
    assert not (set(out) & FORBIDDEN_RAW_TOKENS)
