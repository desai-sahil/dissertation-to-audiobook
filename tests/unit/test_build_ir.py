from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.cleanup import detect_running_artifacts
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.stages.build_ir import BuildIrStage


def _ctx(tiny_ir_path: Path) -> Context:
    return build_mock_context(Config(), pdf_bytes=b"", mock_ir=tiny_ir_path, log_enabled=False)


def _run(blocks: list[Block], ctx: Context) -> Document:
    return BuildIrStage().run(Document(meta=DocumentMeta(title="t"), blocks=blocks), ctx)


def test_strips_page_numbers(tiny_ir_path: Path) -> None:
    blocks = [
        Block(id="p1", type=BlockType.paragraph, text="Real body text."),
        Block(id="pn", type=BlockType.paragraph, text="7"),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert [b.id for b in out.blocks] == ["p1"]


def test_rejoins_split_symbol(tiny_ir_path: Path) -> None:
    blocks = [Block(id="p1", type=BlockType.paragraph, text="we report g s here")]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert out.blocks[0].text == "we report gs here"


def test_merges_cross_page_syllable_drops_hyphen(tiny_ir_path: Path) -> None:
    blocks = [
        Block(id="a", type=BlockType.paragraph, text="catabolism via en-"),
        Block(id="b", type=BlockType.paragraph, text="zymes control the channel."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert len(out.blocks) == 1
    assert out.blocks[0].text == "catabolism via enzymes control the channel."


def test_merges_cross_page_compound_keeps_hyphen(tiny_ir_path: Path) -> None:
    blocks = [
        Block(id="a", type=BlockType.paragraph, text="could predict species-"),
        Block(id="b", type=BlockType.paragraph, text="specific responses everywhere."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert out.blocks[0].text == "could predict species-specific responses everywhere."


def test_merges_cross_page_sentence(tiny_ir_path: Path) -> None:
    blocks = [
        Block(id="a", type=BlockType.paragraph, text="the dry regime remains poorly"),
        Block(id="b", type=BlockType.paragraph, text="constrained. Independent work shows more."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert len(out.blocks) == 1
    assert (
        out.blocks[0].text
        == "the dry regime remains poorly constrained. Independent work shows more."
    )


def test_strips_repeated_running_header(tiny_ir_path: Path) -> None:
    header = "Stomatal Conductance Thesis"
    blocks = [Block(id=f"h{i}", type=BlockType.paragraph, text=header) for i in range(3)]
    blocks.insert(1, Block(id="body", type=BlockType.paragraph, text="Real prose here."))
    assert detect_running_artifacts(blocks) == {header}
    out = _run(blocks, _ctx(tiny_ir_path))
    assert [b.id for b in out.blocks] == ["body"]


def test_keeps_body_line_repeated_only_twice(tiny_ir_path: Path) -> None:
    line = "A repeated but genuine line."
    blocks = [Block(id=f"x{i}", type=BlockType.paragraph, text=line) for i in range(2)]
    assert detect_running_artifacts(blocks) == set()


def test_merges_title_spillover_and_warns(tiny_ir_path: Path) -> None:
    ctx = _ctx(tiny_ir_path)
    blocks = [
        Block(id="h", type=BlockType.heading, section="6.3", text="Coupling with OnGuard"),
        Block(id="frag", type=BlockType.paragraph, text="and A–gs modeling"),
        Block(id="body", type=BlockType.paragraph, text="At present the model resolves signaling."),
    ]
    out = BuildIrStage().run(Document(meta=DocumentMeta(title="t"), blocks=blocks), ctx)
    assert out.blocks[0].text == "Coupling with OnGuard and A–gs modeling"
    assert [b.id for b in out.blocks] == ["h", "body"]
    assert any("wrapped-title" in w.reason for w in ctx.warnings.items)


def test_reference_paragraph_becomes_backmatter(tiny_ir_path: Path) -> None:
    # classified as a reference, then the References region is tagged backmatter (skipped).
    blocks = [Block(id="r", type=BlockType.paragraph, text="[12] Smith. A title.")]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert out.blocks[0].type is BlockType.backmatter


def test_tags_references_region_from_paragraph(tiny_ir_path: Path) -> None:
    blocks = [
        Block(id="body", type=BlockType.paragraph, text="Body ends here."),
        Block(id="refhdr", type=BlockType.paragraph, text="References"),
        Block(id="r1", type=BlockType.reference_list, text="[1] Smith. A title."),
        Block(id="doi", type=BlockType.paragraph, text="DOI: 10.1/x."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    kinds = {b.id: b.type for b in out.blocks}
    assert kinds["body"] is BlockType.paragraph
    assert kinds["refhdr"] is BlockType.backmatter
    assert kinds["r1"] is BlockType.backmatter
    assert kinds["doi"] is BlockType.backmatter


def test_markdown_bulleted_reference_not_absorbed_by_data_availability(tiny_ir_path: Path) -> None:
    # Marker drops the repeated "Bibliography" heading and lists entries as "- [1] ...". A Data
    # Availability note ends in a URL (no period), so without typing the list first the merge
    # would swallow the whole bibliography into that paragraph and speak it. It must not.
    blocks = [
        Block(id="da", type=BlockType.paragraph, text="All codes can be found at https://x.io/repo"),
        Block(id="r1", type=BlockType.paragraph, text="- [1] A. Author. A title. Journal, 2019."),
        Block(id="r2", type=BlockType.paragraph, text="- [2] B. Writer. Another. Journal, 2020."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    kinds = {b.id: b.type for b in out.blocks}
    assert kinds["da"] is BlockType.paragraph  # the note stays its own spoken block
    assert "[1]" not in out.blocks[0].text  # the references were NOT absorbed into it
    assert kinds["r1"] is BlockType.backmatter and kinds["r2"] is BlockType.backmatter


def test_per_chapter_bibliography_does_not_run_away(tiny_ir_path: Path) -> None:
    # A references region ends at the next chapter heading; tagging must not swallow it.
    blocks = [
        Block(id="r1", type=BlockType.paragraph, text="- [1] A. Author. A title. 2019."),
        Block(id="ch2", type=BlockType.heading, chapter=2, text="CHAPTER 2"),
        Block(id="body2", type=BlockType.paragraph, text="The second chapter body continues."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    kinds = {b.id: b.type for b in out.blocks}
    assert kinds["r1"] is BlockType.backmatter
    assert kinds["ch2"] is BlockType.heading and kinds["body2"] is BlockType.paragraph


def test_attaches_section_to_body_paragraphs(tiny_ir_path: Path) -> None:
    blocks = [
        Block(id="h", type=BlockType.heading, section="6.2", text="Results"),
        Block(id="p", type=BlockType.paragraph, text="A finding in this section."),
    ]
    out = _run(blocks, _ctx(tiny_ir_path))
    assert out.blocks[1].section == "6.2"


def test_section_heading_with_no_body_warns(tiny_ir_path: Path) -> None:
    ctx = _ctx(tiny_ir_path)
    blocks = [
        Block(id="h1", type=BlockType.heading, section="6.1", text="Intro"),
        Block(id="h2", type=BlockType.heading, section="6.2", text="Results"),
    ]
    BuildIrStage().run(Document(meta=DocumentMeta(title="t"), blocks=blocks), ctx)
    assert any("no body" in w.reason for w in ctx.warnings.items)


def test_chapter_title_with_no_body_does_not_warn(tiny_ir_path: Path) -> None:
    ctx = _ctx(tiny_ir_path)
    blocks = [
        Block(id="ch", type=BlockType.heading, chapter=6, text="Conclusions"),
        Block(id="sec", type=BlockType.heading, section="6.1", text="Intro"),
        Block(id="p", type=BlockType.paragraph, text="Body."),
    ]
    BuildIrStage().run(Document(meta=DocumentMeta(title="t"), blocks=blocks), ctx)
    assert not any("Conclusions" in w.reason for w in ctx.warnings.items)
