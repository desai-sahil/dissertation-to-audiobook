from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.citation_naturalize import parse_naturalization, render_citation
from thesis_audiobook.config import Config
from thesis_audiobook.ir import BibEntry, Block, BlockType, Citation, Document, DocumentMeta
from thesis_audiobook.stages.citations import CitationsStage


class FakeCiteLlm:
    def __init__(self, json_out: str) -> None:
        self.json_out = json_out
        self.calls = 0

    def complete(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> str:
        self.calls += 1
        return self.json_out


def test_parse_naturalization_handles_fenced_and_garbage() -> None:
    assert parse_naturalization('```json\n{"b1":{"5":"as_shown_by"}}\n```') == {
        "b1": {"5": "as_shown_by"}
    }
    assert parse_naturalization("a mock gloss for input abcd") == {}  # offline mock -> empty


def test_render_citation_is_bounded() -> None:
    assert (
        render_citation("as_shown_by", "Jain", "twenty twenty-one")
        == "as shown by Jain in twenty twenty-one"
    )
    assert (
        render_citation("narrative", "Jain and Smith", "twenty ten")
        == "Jain and Smith, in twenty ten,"
    )
    # An unknown "style" (e.g. an injected sentence) or a missing field renders nothing.
    assert render_citation("which was fabricated", "Jain", "twenty twenty-one") is None
    assert render_citation("as_shown_by", "", "twenty twenty-one") is None
    assert render_citation("as_shown_by", "Jain", "") is None


def _doc(
    *,
    authors: list[str] | None = None,
    year: int | None = 2021,
    text: str = "This was demonstrated [5].",
) -> Document:
    return Document(
        meta=DocumentMeta(title="t"),
        blocks=[Block(id="b1", type=BlockType.paragraph, text=text)],
        citations={"5": Citation(marker="[5]", bib_key="k")},
        bibliography={
            "k": BibEntry(key="k", authors=["Jain"] if authors is None else authors, year=year)
        },
    )


def _run(doc: Document, json_out: str, tiny_ir_path: Path) -> str:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ctx.llm = FakeCiteLlm(json_out)
    CitationsStage().run(doc, ctx)
    return doc.blocks[0].spoken or ""


def test_naturalizer_renders_chosen_style_and_caches(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    llm = FakeCiteLlm('{"b1": {"5": "as_shown_by"}}')
    ctx.llm = llm
    doc = _doc()
    CitationsStage().run(doc, ctx)
    assert doc.blocks[0].spoken == "This was demonstrated as shown by Jain in twenty twenty-one."
    assert llm.calls == 1
    CitationsStage().run(_doc(), ctx)  # fresh identical doc -> cache hit
    assert llm.calls == 1


def test_naturalizer_cannot_inject_text(tiny_ir_path: Path) -> None:
    # A bogus "style" that is actually a sentence injects nothing: only known styles render.
    spoken = _run(_doc(), '{"b1": {"5": "which was completely fabricated"}}', tiny_ir_path)
    assert "fabricated" not in spoken
    assert "Jain twenty twenty-one" in spoken  # deterministic fallback


def test_naturalizer_skips_entry_with_no_author_or_year(tiny_ir_path: Path) -> None:
    spoken = _run(
        _doc(authors=[], year=None, text="The result holds [5]."),
        '{"b1": {"5": "as_shown_by"}}',
        tiny_ir_path,
    )
    assert "The result holds" in spoken
    assert "as shown" not in spoken  # not naturalized; empty citation contributes nothing


def test_naturalizer_inline_author_reads_year_only(tiny_ir_path: Path) -> None:
    # The model picks a name-bearing style, but the author is named inline, so we force
    # year-only and the name is not doubled.
    spoken = _run(
        _doc(text="Jain et al. [5] showed the effect."),
        '{"b1": {"5": "as_shown_by"}}',
        tiny_ir_path,
    )
    assert spoken.count("Jain") == 1
    assert "in twenty twenty-one" in spoken


def test_naturalizer_is_noop_under_mock_llm(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)  # MockLlm
    doc = _doc()
    CitationsStage().run(doc, ctx)
    assert "Jain twenty twenty-one" in (doc.blocks[0].spoken or "")
