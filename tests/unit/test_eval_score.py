from __future__ import annotations

from pathlib import Path

from eval.run import CORPUS, score_corpus_dir
from eval.score import (
    Labels,
    StructureResult,
    score_citation_strip,
    score_raw_token_leak,
    score_structure,
    score_value_preservation,
)


def _labels(**kw: object) -> Labels:
    base: dict[str, object] = {"thesis_id": "t"}
    base.update(kw)
    return Labels.model_validate(base)


def test_structure_f1_penalizes_miss_and_over_detection() -> None:
    labels = _labels(expected_chapters=["a", "b", "c", "d", "e", "f"])  # 6 expected
    assert score_structure(StructureResult(chapters_detected=0), labels).rate == 0.0
    assert score_structure(StructureResult(chapters_detected=6), labels).rate == 1.0
    # under-detection: recall 0.5, precision 1.0 -> F1 0.667
    assert score_structure(StructureResult(chapters_detected=3), labels).rate == 0.667
    # over-detection now COSTS (recall-only used to score this a perfect 1.0): recall 1.0,
    # precision 6/9 -> F1 0.8. This is what catches "VII. REFERENCES" counted as a 7th chapter.
    over = score_structure(StructureResult(chapters_detected=9), labels)
    assert over.rate == 0.8
    assert "extra" in over.misses[0]


def test_citation_strip_substring_and_regex() -> None:
    labels = _labels(must_be_absent=["span id", "doi:", "re:page-?\\w+ to (zero|one)"])
    clean = score_citation_strip("a perfectly clean narration sentence.", labels)
    assert clean.rate == 1.0 and clean.misses == []
    dirty = score_citation_strip(
        'equals "page-nine to zero" and span id here, doi: ten point one', labels
    )
    assert dirty.rate == 0.0
    assert set(dirty.misses) == {"span id", "doi:", "re:page-?\\w+ to (zero|one)"}


def test_citation_strip_is_case_and_whitespace_insensitive() -> None:
    labels = _labels(must_be_absent=["span id"])
    # leak survives casing and a line break between the tokens
    assert score_citation_strip("a SPAN\n  ID leak", labels).rate == 0.0


def test_value_preservation() -> None:
    labels = _labels(must_be_present=["water potential", "one point zero one"])
    survived = score_value_preservation(
        "the water potential rose to one point zero one bar", labels
    )
    assert survived.rate == 1.0
    lost = score_value_preservation("the water potential rose", labels)
    assert lost.rate == 0.5 and lost.misses == ["one point zero one"]


def test_raw_token_leak() -> None:
    assert score_raw_token_leak("clean spoken prose").rate == 1.0
    leaked = score_raw_token_leak("a 50% rise of ±2 here")
    assert leaked.rate == 0.0
    assert any("%" in m for m in leaked.misses) and any("±" in m for m in leaked.misses)


def test_raw_token_leak_ignores_ssml_but_catches_foreign_markup() -> None:
    # SSML pause tags are speech directives, not narrated symbols -> not a leak.
    assert score_raw_token_leak('one.<break time="0.8s"/> two.').rate == 1.0
    # a leaked extraction tag (angle brackets that are NOT SSML) still trips the check.
    assert score_raw_token_leak('a <span id="page-9-0"></span> leak').rate == 0.0


def test_empty_label_set_is_vacuously_perfect() -> None:
    # a thesis with nothing labeled on a dimension should not drag the score down
    assert score_value_preservation("anything", _labels()).rate == 1.0
    assert score_citation_strip("anything", _labels()).rate == 1.0


# --- baseline regression gate: the committed corpus encodes the treadmill. ---


def test_gao_baseline_is_clean() -> None:
    """Gao is the 'works' thesis: structure detected, no leaks, values survive."""
    score = score_corpus_dir(CORPUS / "gao")
    by_dim = {d.dimension: d for d in score.dimensions}
    assert by_dim["structure (chapters)"].rate == 1.0  # 4/4 chapters
    assert by_dim["citation/markup strip"].rate == 1.0  # no markup leaks
    assert by_dim["value preservation"].rate == 1.0  # all sampled values survive
    assert by_dim["raw-token leak (clean=1)"].rate == 1.0  # only SSML breaks, no raw symbols


def test_zhu_baseline_shows_the_treadmill() -> None:
    """Zhu is the failure that motivated v2: structure collapsed, markup leaked, a value lost.
    This test pins the v1 baseline; v2 must move these numbers up, not down."""
    score = score_corpus_dir(CORPUS / "zhu")
    by_dim = {d.dimension: d for d in score.dimensions}
    assert by_dim["structure (chapters)"].rate == 0.0  # 0/6 chapters detected
    assert by_dim["citation/markup strip"].rate < 1.0  # span id / doi / page anchors leaked
    assert by_dim["value preservation"].rate < 1.0  # the 1.01 constant lost to shredding


def test_corpus_dirs_are_well_formed() -> None:
    for thesis in ("gao", "zhu"):
        d: Path = CORPUS / thesis
        assert (d / "labels.json").exists()
        assert (d / "result.json").exists()
        assert (d / "script.md").exists()
