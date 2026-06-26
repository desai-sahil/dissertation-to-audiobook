from __future__ import annotations

import pytest

from thesis_audiobook.normalization.segmentation import segment


@pytest.mark.parametrize(
    "text",
    [
        "",
        "One sentence only.",
        "Smith et al. measured gs. The next sentence began.",
        "We used e.g. this and i.e. that. Done.",
        "See https://desai-sahil.github.io/x/ for details. Next.",
        "Compare Fig. 3 vs. Fig. 4 here. End.",
    ],
)
def test_segmentation_conserves(text: str) -> None:
    assert "".join(segment(text)) == text


def test_no_break_on_et_al() -> None:
    segments = segment("Smith et al. measured gs. The next sentence began.")
    assert len(segments) == 2
    assert "et al." in segments[0]


def test_url_stays_in_one_segment() -> None:
    text = "See https://desai-sahil.github.io/x/ now. Next."
    segments = segment(text)
    assert any("https://desai-sahil.github.io/x/" in seg for seg in segments)
