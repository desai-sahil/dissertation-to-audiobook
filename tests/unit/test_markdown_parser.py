from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.adapters.markdown_parser import (
    MarkdownFileParser,
    MarkdownFileUnavailableError,
)
from thesis_audiobook.bootstrap import select_parser_adapters
from thesis_audiobook.config import Config
from thesis_audiobook.ir import BlockType

_MD = "# Introduction\n\nWater potential matters.\n\n## Methods\n\nWe measured things.\n"


def test_markdown_file_parser_reads_headings(tmp_path: Path) -> None:
    md = tmp_path / "thesis.md"
    md.write_text(_MD, encoding="utf-8")
    doc = MarkdownFileParser(md, title="My Thesis").parse(b"")
    assert doc.meta.title == "My Thesis"
    assert any(b.type is BlockType.heading for b in doc.blocks)
    assert any(b.type is BlockType.paragraph for b in doc.blocks)


def test_markdown_file_parser_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(MarkdownFileUnavailableError):
        MarkdownFileParser(tmp_path / "nope.md").parse(b"")


def test_select_parser_adapters_markdown(tmp_path: Path) -> None:
    md = tmp_path / "thesis.md"
    md.write_text(_MD, encoding="utf-8")
    parser, bib = select_parser_adapters(Config(parser_backend="markdown", markdown_path=str(md)))
    assert isinstance(parser, MarkdownFileParser)
    # The markdown backend has no separate bibliography source (empty mock).
    assert bib.parse(b"").bibliography == {}


def test_select_parser_adapters_markdown_requires_path() -> None:
    with pytest.raises(ValueError, match="markdown_path"):
        select_parser_adapters(Config(parser_backend="markdown"))
