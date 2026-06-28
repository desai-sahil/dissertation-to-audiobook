from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, committee_profile
from thesis_audiobook.ir import Document, DocumentMeta
from thesis_audiobook.stages import build_default_pipeline


def _script(tiny_ir_path: Path) -> str:
    ctx = build_mock_context(
        Config(profile=committee_profile()), pdf_bytes=b"x", mock_ir=tiny_ir_path
    )
    doc = build_default_pipeline().run(Document(meta=DocumentMeta(title="x")), ctx)
    assert doc.script is not None
    return doc.script


def test_intro_and_outro(tiny_ir_path: Path) -> None:
    script = _script(tiny_ir_path)
    assert script.startswith("An audiobook rendering of A Tiny Synthetic Thesis")
    assert script.rstrip().endswith("This concludes A Tiny Synthetic Thesis.")


def test_structural_announcements(tiny_ir_path: Path) -> None:
    script = _script(tiny_ir_path)
    assert "Chapter one. Introduction." in script
    assert "Chapter two. Results." in script
    assert "Section two point one, Gas exchange." in script


def test_heading_announcement_strips_leading_enumerator() -> None:
    from thesis_audiobook.ir import Block, BlockType
    from thesis_audiobook.stages.assemble_script import _heading_announcement

    chapter = Block(id="a", type=BlockType.heading, text="I. INTRODUCTION", chapter=1)
    assert _heading_announcement(chapter) == "Chapter one. INTRODUCTION."  # roman "I." dropped
    subsection = Block(id="b", type=BlockType.heading, text="III.A.1. Substrates")
    assert _heading_announcement(subsection) == "Substrates."  # bare title, no "Chapter N"
    plain = Block(id="c", type=BlockType.heading, text="Methods", chapter=2)
    assert _heading_announcement(plain) == "Chapter two. Methods."  # untouched, no enumerator


def test_figure_caption_placed_at_first_reference(tiny_ir_path: Path) -> None:
    script = _script(tiny_ir_path)
    ref_index = script.index("As shown in Figure one")
    caption_index = script.index("Panel A stomatal conductance over time")
    assert ref_index < caption_index


def test_break_tags_present_for_multilingual_v2(tiny_ir_path: Path) -> None:
    assert '<break time="0.8s"/>' in _script(tiny_ir_path)


def test_figure_without_reference_placed_at_end(tiny_ir_path: Path) -> None:
    from thesis_audiobook.ir import Block, BlockType, Figure
    from thesis_audiobook.stages.assemble_script import AssembleScriptStage
    from thesis_audiobook.stages.figures import FiguresStage
    from thesis_audiobook.stages.normalize import NormalizeStage
    from thesis_audiobook.stages.select import SelectStage

    ctx = build_mock_context(
        Config(profile=committee_profile()), pdf_bytes=b"x", mock_ir=tiny_ir_path
    )
    doc = Document(
        meta=DocumentMeta(title="T"),
        blocks=[Block(id="p1", type=BlockType.paragraph, chapter=1, text="Body text here.")],
        figures={
            "orphan": Figure(id="orphan", caption="Fig. 9. an orphan caption.", ref_points=[])
        },
    )
    for stage in (SelectStage(), FiguresStage(), NormalizeStage(), AssembleScriptStage()):
        doc = stage.run(doc, ctx)
    assert doc.script is not None
    # No reference point, so the caption falls back to end-of-section placement.
    assert "an orphan caption" in doc.script
    assert doc.script.index("Body text here") < doc.script.index("an orphan caption")
