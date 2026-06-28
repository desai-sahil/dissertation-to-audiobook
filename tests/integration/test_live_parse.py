from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.live
def test_live_marker_parse(sample_pdf: Path) -> None:
    """Runs the real Marker parser on the sample. Needs marker-pdf installed.

    Skipped by default; run with `pytest -m live` on a machine with marker-pdf. Citations are
    genericized downstream with no bibliography, so there is no separate bib/GROBID step.
    """
    from thesis_audiobook.adapters.marker_parser import MarkerParser

    document = MarkerParser().parse(sample_pdf.read_bytes())
    assert len(document.blocks) > 0
