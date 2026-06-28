from __future__ import annotations

from thesis_audiobook.curate import AcronymRule, PronunciationPlan, TermRule
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.ledger import render_ledger
from thesis_audiobook.script_repair import AppliedRepair, RejectedRepair
from thesis_audiobook.structurer import Reclassification


def _doc() -> Document:
    return Document(
        meta=DocumentMeta(title="A Thesis"),
        blocks=[
            Block(id="m1", type=BlockType.heading, text="INTRODUCTION", chapter=1),
            Block(id="m2", type=BlockType.heading, text="Background", chapter=1, section="1"),
            Block(id="m3", type=BlockType.heading, text="RESULTS", chapter=2),
            Block(id="m4", type=BlockType.backmatter, text="APPENDIX"),
            Block(id="m5", type=BlockType.backmatter, text="import numpy as np"),
        ],
    )


def test_ledger_lists_chapters_and_skipped_backmatter() -> None:
    out = render_ledger(_doc(), [], None, [], [])
    assert "Chapters detected: 2" in out
    assert "1. INTRODUCTION" in out and "2. RESULTS" in out
    assert "Back matter skipped" in out and "2 block(s)" in out
    assert 'from "APPENDIX" onward' in out


def test_ledger_records_curator_and_repairs() -> None:
    plan = PronunciationPlan(
        acronyms=[
            AcronymRule(acronym="SPAC", first_use="soil plant atmosphere", short_form="S P A C")
        ],
        terms=[TermRule(term="AtRBOHD", spoken="arbo D")],
        notes=["unsure about Foo"],
    )
    out = render_ledger(
        _doc(),
        [Reclassification(id="m9", from_type="paragraph", to_type="code", snippet="def f():")],
        plan,
        [
            AppliedRepair(find="spack", replace="S P A C", count=3, reason="acronym"),
            AppliedRepair(
                find="responce", replace="response", count=1, reason="typo", kind="spelling"
            ),
            AppliedRepair(
                find="< 111 >",
                replace="1 1 1",
                count=1,
                reason="miller",
                kind="extraction_artifact",
            ),
        ],
        [RejectedRepair(find="Mott", replace="Mott 2013", why="auditor: added a year")],
    )
    assert "Structurer reclassified 1 block(s)" in out and "def f()" in out
    assert "S P A C" in out and "arbo D" in out
    assert "unsure about Foo" in out
    # applied repairs are grouped into distinct provenance sections by kind
    assert "Auto-repairs (notation vocalization)" in out and "spack" in out
    assert "Author corrections (copy-edit" in out and "responce" in out
    assert "Extraction artifacts re-rendered" in out and "1 1 1" in out
    assert "Rejected / flagged" in out and "added a year" in out


def test_ledger_pipe_in_cell_is_escaped() -> None:
    out = render_ledger(
        _doc(), [], None, [AppliedRepair(find="a|b", replace="c", count=1, reason="x")], []
    )
    assert "a\\|b" in out  # a literal pipe must not break the markdown table
