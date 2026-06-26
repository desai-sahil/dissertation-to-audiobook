from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.adapters.grobid_client import (
    GrobidClient,
    GrobidUnavailableError,
    tei_to_bibresult,
)


def test_tei_to_bibresult(cassette_dir: Path) -> None:
    tei = (cassette_dir / "grobid_sample.tei.xml").read_text(encoding="utf-8")
    result = tei_to_bibresult(tei)

    assert set(result.bibliography) == {"b0", "b1"}
    assert result.bibliography["b0"].authors == ["Smith", "Roe"]
    assert result.bibliography["b0"].year == 2019
    assert result.bibliography["b1"].authors == ["Jones"]
    assert result.bibliography["b1"].year == 2020

    # Inline markers are linked to bibliography ids.
    assert result.citations["1"].bib_key == "b0"
    assert result.citations["2"].bib_key == "b1"


def test_tei_handles_markup_and_published_date() -> None:
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><back><listBibl>'
        '<biblStruct xml:id="b0"><analytic>'
        "<author><persName><surname>van der <hi>Berg</hi></surname></persName></author>"
        '<title level="a">Effects of <hi>ABA</hi> on stomata</title></analytic>'
        '<monogr><imprint><date type="ePub" when="2018"/>'
        '<date type="published" when="2019"/></imprint></monogr>'
        "</biblStruct></listBibl></back></text></TEI>"
    )
    entry = tei_to_bibresult(tei).bibliography["b0"]
    assert entry.authors == ["van der Berg"]  # itertext keeps the markup-wrapped name
    assert entry.title == "Effects of ABA on stomata"  # not truncated at the <hi>
    assert entry.year == 2019  # published date preferred over the earlier ePub date


def test_invalid_tei_raises_typed_error() -> None:
    with pytest.raises(GrobidUnavailableError):
        tei_to_bibresult("<not-xml")


def test_is_alive_false_when_unreachable() -> None:
    # Nothing is listening on this port; must not crash, just report False.
    assert GrobidClient("http://127.0.0.1:1", timeout=1.0).is_alive() is False
