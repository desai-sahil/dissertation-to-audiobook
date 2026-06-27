from __future__ import annotations

from thesis_audiobook.normalization.repetition import collapse_repetition


def test_noop_on_normal_prose() -> None:
    prose = (
        "We found that the passage of water through the outside xylem zone creates a "
        "significant drop in water potential across all upstream components of the continuum "
        "as measured here compared to previously reported values in the literature today."
    )
    out, removed = collapse_repetition(prose)
    assert removed == 0 and out == prose


def test_short_text_is_untouched() -> None:
    out, removed = collapse_repetition("no no no")  # below the span/block thresholds
    assert removed == 0 and out == "no no no"


def test_collapses_exact_periodic_loop() -> None:
    # A period-4 loop with four distinct words does not trip the diversity guard, so this
    # exercises the periodic-collapse pass and the surrounding content survives.
    text = "start " + "alpha beta gamma delta " * 6 + "finish"
    out, removed = collapse_repetition(text)
    assert removed > 0 and out.count("alpha beta gamma delta") == 1
    assert out.startswith("start") and out.endswith("finish")


def test_truncates_fuzzy_ocr_loop_keeping_readable_head() -> None:
    head = "Transpiration rate measured along the maize leaf for each of the eight regions shown."
    garble = " ".join(["(E, E, E, E, assimilation rate"] * 30)
    out, removed = collapse_repetition(f"{head} {garble}")
    assert removed > 50
    assert out.startswith("Transpiration rate measured along the maize leaf")
    # the degenerate tail is gone, not merely shortened
    assert out.count("assimilation rate") <= 2
