"""LLM pronunciation curator: pure plan parsing/application + the cached stage."""

from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.curate import apply_plan, parse_plan
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.stages.curate import CurateStage


def test_abbreviation_map_introduces_then_spells_across_document() -> None:
    # M7: gs (lowercase, space-separated after math cleanup) and OXZ are introduced once on
    # first global use, then spoken as the spelled short form everywhere after - even across
    # separate blocks (whole-document, not per-block).
    plan = parse_plan(
        '{"acronyms":[{"acronym":"g s","first_use":"stomatal conductance","short_form":"g s"},'
        '{"acronym":"OXZ","first_use":"outside xylem zone","short_form":"O X Z"}]}'
    )
    out = apply_plan(
        [
            "We measured g s in the leaf.",
            "Later, g s dropped and the OXZ collapsed.",
            "The OXZ recovered overnight.",
        ],
        plan,
    )
    assert out[0] == "We measured stomatal conductance (g s) in the leaf."
    assert out[1] == "Later, g s dropped and the outside xylem zone (O X Z) collapsed."
    assert out[2] == "The O X Z recovered overnight."  # already introduced -> spelled form


PLAN_JSON = (
    '{"acronyms":[{"acronym":"ABA","first_use":"abscisic acid","short_form":"A B A"},'
    '{"acronym":"VPD","first_use":"vapor pressure deficit","short_form":"V P D"}],'
    '"terms":[{"term":"AtRBOHD","spoken":"arbo D"}],'
    '"notation":[{"written":"psi apo ssc","spoken":"apoplastic subsidiary cell water potential"}],'
    '"notes":["unsure about XYZ"]}'
)


class FakePlanLlm:
    def __init__(self, plan_json: str) -> None:
        self.plan_json = plan_json
        self.calls = 0

    def complete(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> str:
        self.calls += 1
        return self.plan_json


def test_parse_plan_valid_fenced_and_garbage() -> None:
    plan = parse_plan(f"```json\n{PLAN_JSON}\n```")
    assert [a.acronym for a in plan.acronyms] == ["ABA", "VPD"]
    assert plan.terms[0].spoken == "arbo D"
    # A non-JSON response (the offline mock) degrades to an empty plan, not a crash.
    assert parse_plan("a mock gloss for input dbadfecb").is_empty()


def test_apply_plan_acronym_first_use_author_aware() -> None:
    texts = [
        "We studied abscisic acid (ABA) under drought.",
        "Later ABA increased and VPD rose.",
        "The AtRBOHD gene and psi apo ssc both mattered.",
    ]
    out = apply_plan(texts, parse_plan(PLAN_JSON))
    # Author already defined ABA, so first use is just the short form (no double intro).
    assert out[0] == "We studied abscisic acid (A B A) under drought."
    # ABA already introduced -> short form; VPD never defined -> we introduce it.
    assert out[1] == "Later A B A increased and vapor pressure deficit (V P D) rose."
    # Terms + notation are plain substitutions.
    assert out[2] == "The arbo D gene and apoplastic subsidiary cell water potential both mattered."


def test_apply_plan_single_pass_no_reexpansion() -> None:
    # A term's spoken form that contains an acronym token must NOT be re-expanded.
    plan = parse_plan(
        '{"acronyms":[{"acronym":"PD","first_use":"plasmodesmata","short_form":"P D"}],'
        '"terms":[{"term":"gene1","spoken":"the PD pathway"}]}'
    )
    assert apply_plan(["The gene1 is key."], plan) == ["The the PD pathway is key."]
    # An acronym's own output must not be re-expanded by a substring acronym rule.
    plan2 = parse_plan(
        '{"acronyms":[{"acronym":"ABA","first_use":"abscisic acid","short_form":"A B A"},'
        '{"acronym":"A","first_use":"ampere","short_form":"amp"}]}'
    )
    assert apply_plan(["We used ABA today."], plan2) == ["We used abscisic acid (A B A) today."]


def test_apply_plan_skips_single_letter_and_greek_keys() -> None:
    # Single-letter symbols (E, A) collide with middle initials and the article "A"; a bare
    # Greek-letter name (zeta) is overloaded. Neither is expanded in prose.
    plan = parse_plan(
        '{"acronyms":[{"acronym":"E","first_use":"transpiration rate","short_form":"E"},'
        '{"acronym":"A","first_use":"assimilation rate","short_form":"A"}],'
        '"notation":[{"written":"zeta","spoken":"relative FRET efficiency"},'
        '{"written":"psi xyl","spoken":"xylem water potential"}]}'
    )
    out = apply_plan(
        ["Annika E. Huber gave guidance.", "A hearty thanks; zeta rose as psi xyl fell."], plan
    )
    assert out[0] == "Annika E. Huber gave guidance."  # middle initial untouched
    assert "transpiration rate" not in out[0]
    assert out[1].startswith("A hearty thanks")  # article untouched
    assert "zeta rose" in out[1] and "relative FRET" not in out[1]  # greek name kept
    assert "xylem water potential" in out[1]  # multi-word notation still expands


def test_apply_plan_dehyphenates() -> None:
    plan = parse_plan(
        '{"dehyphenations":[{"broken":"me-asurable","fixed":"measurable"},'
        '{"broken":"encom-pass","fixed":"encompass"}]}'
    )
    assert apply_plan(["a me-asurable effect that encom-pass all"], plan) == [
        "a measurable effect that encompass all"
    ]
    # word-bounded: not matched inside a larger token
    assert apply_plan(["Xme-asurableY and ame-asurable"], plan) == [
        "Xme-asurableY and ame-asurable"
    ]


def test_apply_plan_skips_empty_keys() -> None:
    plan = parse_plan('{"terms":[{"term":"","spoken":"X"},{"term":"gene1","spoken":"arbo"}]}')
    assert apply_plan(["a gene1 b"], plan) == ["a arbo b"]


def test_format_qa_renders_notes_only_and_escapes_pipes() -> None:
    from thesis_audiobook.cli import _format_qa
    from thesis_audiobook.curate import PronunciationPlan, TermRule

    notes_only = _format_qa(PronunciationPlan(notes=["unsure about XYZ"]))
    assert "unsure about XYZ" in notes_only and "Notes" in notes_only
    piped = _format_qa(PronunciationPlan(terms=[TermRule(term="a|b", spoken="c|d")]))
    assert "\\|" in piped
    assert _format_qa(None).strip().endswith("nothing to curate).")


def _doc() -> Document:
    return Document(
        meta=DocumentMeta(title="t"),
        blocks=[
            Block(id="b1", type=BlockType.paragraph, text="We studied abscisic acid (ABA) here."),
            Block(id="b2", type=BlockType.paragraph, text="Later ABA fell."),
        ],
    )


def test_curate_stage_applies_plan_and_caches(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    llm = FakePlanLlm(PLAN_JSON)
    ctx.llm = llm

    doc = _doc()
    CurateStage().run(doc, ctx)
    assert doc.blocks[0].spoken == "We studied abscisic acid (A B A) here."
    assert doc.blocks[1].spoken == "Later A B A fell."
    assert ctx.pronunciation_plan is not None and ctx.pronunciation_plan.acronyms
    assert llm.calls == 1

    # A fresh doc with the same source text reuses the cached plan: no second model call.
    fresh = _doc()
    CurateStage().run(fresh, ctx)
    assert fresh.blocks[0].spoken == "We studied abscisic acid (A B A) here."
    assert llm.calls == 1


def test_curate_stage_respects_no_curate_flag(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(curate=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    llm = FakePlanLlm(PLAN_JSON)
    ctx.llm = llm
    doc = _doc()
    CurateStage().run(doc, ctx)
    assert doc.blocks[0].spoken is None  # untouched
    assert ctx.pronunciation_plan is None
    assert llm.calls == 0  # no model call when disabled


def test_curate_with_real_llm_trips_cost_guard(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ctx.llm = AnthropicClient()  # the autouse guard makes any real .complete raise
    with pytest.raises(RuntimeError, match="live external call"):
        CurateStage().run(_doc(), ctx)
