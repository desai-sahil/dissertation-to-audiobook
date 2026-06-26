from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.cartographer import (
    apply_map,
    build_fingerprint,
    build_outline,
    effective_decision,
    parse_map,
    render_structure_md,
)
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context
from thesis_audiobook.ir import (
    Block,
    BlockType,
    Document,
    DocumentMeta,
    Region,
    RegionDecision,
    RegionKind,
    StructureMap,
)
from thesis_audiobook.stages.cartographer import CartographerStage


def _b(
    bid: str,
    btype: BlockType,
    text: str,
    chapter: int | None = None,
    page: int | None = None,
) -> Block:
    return Block(id=bid, type=btype, text=text, chapter=chapter, page=page)


def _doc(*blocks: Block) -> Document:
    return Document(meta=DocumentMeta(title="A Thesis", author="P. Author"), blocks=list(blocks))


def _region(
    kind: RegionKind,
    first: str,
    last: str,
    *,
    decision: RegionDecision = RegionDecision.include,
    chapter: int | None = None,
    heading_anchored: bool = True,
    kc: float = 0.95,
    dc: float = 0.95,
) -> Region:
    return Region(
        kind=kind,
        decision=decision,
        first_block_id=first,
        last_block_id=last,
        chapter=chapter,
        heading_anchored=heading_anchored,
        kind_confidence=kc,
        decision_confidence=dc,
    )


class _FakeLlm:
    """Returns a canned response and counts calls (cost guard ignores non-adapter LLMs)."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> str:
        self.calls += 1
        return self.response


# --- IR types round-trip ----------------------------------------------------------------


def test_structure_map_round_trips() -> None:
    smap = StructureMap(regions=[_region(RegionKind.abstract, "b1", "b2")])
    assert StructureMap.model_validate(smap.model_dump()) == smap


# --- parse_map --------------------------------------------------------------------------


def test_parse_map_non_json_is_empty() -> None:
    # The offline MockLlm returns exactly this shape; it must degrade to a no-op.
    assert parse_map("a mock gloss for input abcdefgh").is_empty()


def test_parse_map_strips_fences_and_parses() -> None:
    raw = '```json\n{"regions": [{"kind": "abstract", "decision": "include", '
    raw += '"first_block_id": "b1", "last_block_id": "b1"}]}\n```'
    smap = parse_map(raw)
    assert len(smap.regions) == 1
    assert smap.regions[0].kind is RegionKind.abstract


def test_parse_map_bad_enum_is_empty() -> None:
    assert parse_map(
        '{"regions": [{"kind": "not_a_kind", "decision": "include", '
        '"first_block_id": "b1", "last_block_id": "b1"}]}'
    ).is_empty()


# --- build_outline / fingerprint --------------------------------------------------------


def test_outline_shows_blocks_and_rederives_buried_structure() -> None:
    doc = _doc(
        _b("b1", BlockType.heading, "CHAPTER 1", chapter=1, page=1),
        _b("b2", BlockType.paragraph, "First para.", page=1),
        _b("b3", BlockType.backmatter, "CHAPTER 2", page=2),  # latch-buried heading
        _b("b4", BlockType.backmatter, "Body of chapter two.", page=2),  # buried prose
        _b("b5", BlockType.reference_list, "[1] Ref.", page=3),
    )
    lines = build_outline(doc).splitlines()
    assert lines[0].startswith("TITLE:")
    assert any(line.startswith("b1 | ") and "heading" in line for line in lines)
    # The latch-buried "CHAPTER 2" is re-derived to a heading so the model can see it.
    assert any(line.startswith("b3 | ") and "heading" in line for line in lines)
    # Buried prose shows as a body block, never the raw 'backmatter' type.
    assert any(
        line.startswith("b4 | ") and "paragraph" in line and "backmatter" not in line
        for line in lines
    )
    assert any(line.startswith("b5 | ") and "reference_list" in line for line in lines)
    assert build_outline(doc) == "\n".join(lines)  # deterministic


def test_outline_summarizes_long_run_middle() -> None:
    blocks = [_b(f"b{k}", BlockType.paragraph, f"Paragraph {k}.") for k in range(1, 21)]
    lines = build_outline(_doc(*blocks)).splitlines()
    assert any("more blocks:" in line for line in lines)  # middle summarized
    assert any(line.startswith("b1 | ") for line in lines)  # head shown
    assert any(line.startswith("b20 | ") for line in lines)  # tail shown


def test_fingerprint_changes_with_content() -> None:
    a = _doc(_b("b1", BlockType.paragraph, "one"))
    b = _doc(_b("b1", BlockType.paragraph, "two"))
    assert build_fingerprint(a) != build_fingerprint(b)


# --- apply_map --------------------------------------------------------------------------


def test_apply_map_empty_is_strict_no_op() -> None:
    doc = _doc(_b("b1", BlockType.paragraph, "Body."))
    assert apply_map(doc, StructureMap()) == []
    assert doc.blocks[0].type is BlockType.paragraph
    assert doc.blocks[0].notes == []


def test_apply_map_never_mutates_text_or_spoken() -> None:
    doc = _doc(
        _b("b1", BlockType.paragraph, "Real prose."),
        _b("b2", BlockType.backmatter, "[1] A reference."),
    )
    before = [b.text for b in doc.blocks]
    apply_map(
        doc,
        StructureMap(
            regions=[
                _region(RegionKind.chapter_body, "b1", "b1", chapter=1),
                _region(RegionKind.per_chapter_bibliography, "b2", "b2", heading_anchored=False),
            ]
        ),
    )
    assert [b.text for b in doc.blocks] == before
    assert all(b.spoken is None for b in doc.blocks)


def test_apply_map_scopes_per_chapter_bib_and_repairs_latch_overreach() -> None:
    # Simulates build_ir's one-way latch having wrongly swept Chapter 2 into backmatter.
    doc = _doc(
        _b("b1", BlockType.heading, "CHAPTER 1", chapter=1),
        _b("b2", BlockType.paragraph, "Chapter one body."),
        _b("b3", BlockType.backmatter, "[1] Ref one."),  # ch1 bibliography (latched)
        _b("b4", BlockType.backmatter, "CHAPTER 2"),  # over-reach
        _b("b5", BlockType.backmatter, "Chapter two body."),  # over-reach
    )
    apply_map(
        doc,
        StructureMap(
            regions=[
                _region(RegionKind.chapter_body, "b1", "b2", chapter=1),
                _region(RegionKind.per_chapter_bibliography, "b3", "b3", heading_anchored=False),
                _region(RegionKind.chapter_body, "b4", "b5", chapter=2),
            ]
        ),
    )
    # Chapter 2 prose recovered from backmatter; bibliography stays a reference list.
    assert doc.blocks[2].type is BlockType.reference_list
    assert doc.blocks[3].type is BlockType.heading  # "CHAPTER 2" re-derived
    assert doc.blocks[4].type is BlockType.paragraph


def test_apply_map_appendix_becomes_backmatter() -> None:
    doc = _doc(_b("b1", BlockType.heading, "APPENDIX A"), _b("b2", BlockType.paragraph, "Detail."))
    apply_map(doc, StructureMap(regions=[_region(RegionKind.appendix, "b1", "b2", chapter=1)]))
    assert all(b.type is BlockType.backmatter for b in doc.blocks)


def test_apply_map_silent_deletion_guard_warns_on_prose_to_skip() -> None:
    doc = _doc(_b("b1", BlockType.paragraph, "A genuine chapter paragraph."))
    warnings = apply_map(
        doc,
        StructureMap(
            regions=[
                _region(RegionKind.per_chapter_bibliography, "b1", "b1", heading_anchored=False)
            ]
        ),
    )
    assert doc.blocks[0].type is BlockType.reference_list
    assert any("demoted spoken" in w.reason for w in warnings)


def test_apply_map_drops_bad_span_with_warning() -> None:
    doc = _doc(_b("b1", BlockType.paragraph, "Body."))
    warnings = apply_map(
        doc, StructureMap(regions=[_region(RegionKind.chapter_body, "ghost1", "ghost2")])
    )
    assert doc.blocks[0].type is BlockType.paragraph  # untouched
    assert any("bad span" in w.reason for w in warnings)


def test_apply_map_drops_overlapping_region() -> None:
    doc = _doc(
        _b("b1", BlockType.paragraph, "One."),
        _b("b2", BlockType.paragraph, "Two."),
        _b("b3", BlockType.paragraph, "Three."),
    )
    warnings = apply_map(
        doc,
        StructureMap(
            regions=[
                _region(RegionKind.chapter_body, "b1", "b2", chapter=1),
                _region(RegionKind.appendix, "b2", "b3", chapter=1),  # overlaps b2
            ]
        ),
    )
    assert any("overlapping" in w.reason for w in warnings)
    # The first region won; the overlapper was dropped, so b3 stays prose.
    assert doc.blocks[2].type is BlockType.paragraph


def test_apply_map_coverage_guard_flags_uncovered_prose_left_skipped() -> None:
    doc = _doc(
        _b("b1", BlockType.paragraph, "Covered prose."),
        _b("b2", BlockType.backmatter, "This sentence reads like real prose."),
    )
    warnings = apply_map(
        doc, StructureMap(regions=[_region(RegionKind.chapter_body, "b1", "b1", chapter=1)])
    )
    assert any("not covered by any region" in w.reason for w in warnings)


def test_apply_map_unlabeled_spoken_region_warns() -> None:
    doc = _doc(_b("b1", BlockType.paragraph, "Unlabeled abstract prose."))
    warnings = apply_map(
        doc,
        StructureMap(regions=[_region(RegionKind.abstract, "b1", "b1", heading_anchored=False)]),
    )
    assert any("UNLABELED" in w.reason for w in warnings)


def test_apply_map_review_decision_warns() -> None:
    doc = _doc(_b("b1", BlockType.heading, "APPENDIX A"))
    warnings = apply_map(
        doc,
        StructureMap(
            regions=[_region(RegionKind.appendix, "b1", "b1", decision=RegionDecision.review)]
        ),
    )
    assert any("flagged for review" in w.reason for w in warnings)


def test_apply_map_fills_missing_chapter_but_warns_on_conflict() -> None:
    doc = _doc(
        _b("b1", BlockType.paragraph, "No chapter yet."),
        _b("b2", BlockType.paragraph, "Wrong chapter.", chapter=9),
    )
    warnings = apply_map(
        doc, StructureMap(regions=[_region(RegionKind.chapter_body, "b1", "b2", chapter=3)])
    )
    assert doc.blocks[0].chapter == 3  # filled
    assert doc.blocks[1].chapter == 9  # never silently renumbered
    assert any("kept block value" in w.reason for w in warnings)


def test_apply_map_adopts_title_found_verbatim() -> None:
    doc = _doc(
        _b("b1", BlockType.paragraph, "Transducing Thermodynamic State of Water"),
        _b("b2", BlockType.paragraph, "Body."),
    )
    apply_map(
        doc,
        StructureMap(
            title="Transducing Thermodynamic State of Water",
            regions=[_region(RegionKind.chapter_body, "b2", "b2", chapter=1)],
        ),
    )
    assert doc.meta.title == "Transducing Thermodynamic State of Water"


def test_apply_map_rejects_fabricated_title() -> None:
    doc = _doc(_b("b1", BlockType.paragraph, "Real content only."))
    warnings = apply_map(
        doc,
        StructureMap(
            title="A Title That Is Nowhere In The Document",
            regions=[_region(RegionKind.chapter_body, "b1", "b1", chapter=1)],
        ),
    )
    assert doc.meta.title == "A Thesis"  # unchanged default; never fabricated
    assert any("not found verbatim" in w.reason for w in warnings)


# --- render_structure_md ----------------------------------------------------------------


def test_effective_decision_is_kind_and_profile_driven() -> None:
    # Spoken kinds always include (the user's front-matter choices live here).
    assert effective_decision(RegionKind.biographical_sketch, False) == "include"
    assert effective_decision(RegionKind.abstract, False) == "include"
    # Navigation/reference kinds always skip.
    assert effective_decision(RegionKind.table_of_contents, False) == "skip"
    assert effective_decision(RegionKind.per_chapter_bibliography, False) == "skip"
    # Appendices ride the profile flag.
    assert effective_decision(RegionKind.appendix, False) == "skip"
    assert effective_decision(RegionKind.appendix, True) == "include"
    assert effective_decision(RegionKind.unknown, False) == "review"


def test_render_shows_effective_decision_not_llm_suggestion() -> None:
    # The model "decided" skip, but a biographical sketch is a kept (spoken) kind, so the
    # map must show the real outcome: include.
    doc = _doc(_b("b1", BlockType.paragraph, "Bio."))
    md = render_structure_md(
        StructureMap(
            regions=[
                _region(RegionKind.biographical_sketch, "b1", "b1", decision=RegionDecision.skip)
            ]
        ),
        doc,
    )
    assert "| include |" in md
    # And an appendix shows skip by default, include when the profile opts in.
    appx_doc = _doc(_b("b1", BlockType.heading, "APPENDIX A"))
    appx = StructureMap(regions=[_region(RegionKind.appendix, "b1", "b1")])
    assert "| skip |" in render_structure_md(appx, appx_doc)
    assert "| include |" in render_structure_md(appx, appx_doc, include_appendices=True)


def test_render_flags_unknown_region() -> None:
    # An unknown region shows decision "review" AND an "unknown" flag (it is left as-is,
    # not auto-held, so the human must check it).
    doc = _doc(_b("b1", BlockType.paragraph, "Something odd."))
    md = render_structure_md(StructureMap(regions=[_region(RegionKind.unknown, "b1", "b1")]), doc)
    assert "| review |" in md and "unknown" in md


def test_render_structure_md_empty_and_populated() -> None:
    assert "no map" in render_structure_md(StructureMap(), _doc(_b("b1", BlockType.paragraph, "x")))
    doc = _doc(_b("b1", BlockType.heading, "APPENDIX A"))
    md = render_structure_md(
        StructureMap(
            regions=[_region(RegionKind.appendix, "b1", "b1", decision=RegionDecision.review)]
        ),
        doc,
    )
    assert "appendix" in md and "Flagged for review" in md


# --- CartographerStage ------------------------------------------------------------------


def _ctx(tiny_ir_path: Path, structure_eval: bool = True) -> Context:
    return build_mock_context(
        Config(structure_eval=structure_eval), pdf_bytes=b"x", mock_ir=tiny_ir_path
    )


def test_stage_mock_llm_is_strict_no_op(tiny_ir_path: Path) -> None:
    ctx = _ctx(tiny_ir_path)  # MockLlm returns non-JSON
    doc = _doc(_b("b1", BlockType.paragraph, "Body."), _b("b2", BlockType.heading, "CHAPTER 1"))
    CartographerStage().run(doc, ctx)
    assert [b.type for b in doc.blocks] == [BlockType.paragraph, BlockType.heading]
    assert ctx.warnings.items == []
    assert ctx.structure_map is not None and ctx.structure_map.is_empty()


def test_stage_disabled_makes_no_llm_call(tiny_ir_path: Path) -> None:
    ctx = _ctx(tiny_ir_path, structure_eval=False)
    fake = _FakeLlm('{"regions": []}')
    ctx.llm = fake
    CartographerStage().run(_doc(_b("b1", BlockType.paragraph, "x")), ctx)
    assert fake.calls == 0


def test_stage_caches_map_across_runs(tiny_ir_path: Path) -> None:
    response = (
        '{"regions": [{"kind": "chapter_body", "decision": "include", '
        '"first_block_id": "b1", "last_block_id": "b1", "chapter": 1, '
        '"heading_anchored": true, "kind_confidence": 0.95, "decision_confidence": 0.95}]}'
    )
    fake = _FakeLlm(response)
    ctx = _ctx(tiny_ir_path)
    ctx.llm = fake

    CartographerStage().run(_doc(_b("b1", BlockType.paragraph, "Body.")), ctx)
    # A fresh, identical document hits the cache (same structural fingerprint) -> no 2nd call.
    CartographerStage().run(_doc(_b("b1", BlockType.paragraph, "Body.")), ctx)
    assert fake.calls == 1


def test_stage_verify_rejects_cached_map_with_foreign_ids() -> None:
    foreign = StructureMap(regions=[_region(RegionKind.chapter_body, "zzz", "zzz")])
    doc = _doc(_b("b1", BlockType.paragraph, "Body."))
    assert CartographerStage._verify(foreign, doc).is_empty()
