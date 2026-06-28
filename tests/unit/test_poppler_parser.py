from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from thesis_audiobook.adapters.poppler_parser import (
    PopplerParser,
    parse_document,
)
from thesis_audiobook.ir import BlockType


def _cassette(cassette_dir: Path) -> str:
    return (cassette_dir / "chapter6.pdftotext.txt").read_text(encoding="utf-8")


def test_parse_document_recovers_sections_in_order(cassette_dir: Path) -> None:
    doc = parse_document(_cassette(cassette_dir))
    sections = [b.section for b in doc.blocks if b.type is BlockType.heading and b.section]
    assert sections == ["6.1", "6.2", "6.3", "6.4", "6.5", "6.6"]


def test_parse_document_finds_references(cassette_dir: Path) -> None:
    doc = parse_document(_cassette(cassette_dir))
    assert any(b.type is BlockType.reference_list for b in doc.blocks)


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler not installed")
def test_real_pdftotext_parse(sample_pdf: Path) -> None:
    doc = PopplerParser().parse(sample_pdf.read_bytes())
    assert len(doc.blocks) > 20
    assert any(b.type is BlockType.heading for b in doc.blocks)
