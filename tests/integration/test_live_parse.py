from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.live
def test_live_marker_and_grobid(sample_pdf: Path) -> None:
    """Runs the real Marker parser and GROBID on the sample. Needs both installed.

    Skipped by default; run with `pytest -m live` on a machine with marker-pdf and a
    GROBID service (default http://localhost:8070).
    """
    from thesis_audiobook.adapters.grobid_client import GrobidClient
    from thesis_audiobook.adapters.marker_parser import MarkerParser

    pdf = sample_pdf.read_bytes()

    document = MarkerParser().parse(pdf)
    assert len(document.blocks) > 0

    client = GrobidClient()
    if not client.is_alive():
        pytest.skip("GROBID service is not running")
    result = client.parse(pdf)
    assert len(result.bibliography) > 0
