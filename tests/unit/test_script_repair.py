from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Chunk, Document, DocumentMeta
from thesis_audiobook.script_repair import (
    ScriptRepair,
    apply_script_repairs,
    is_safe_script_repair,
    parse_script_repair_plan,
)
from thesis_audiobook.stages.script_repair import ScriptRepairStage

_PLAN = (
    '{"summary":"minor fixes","repairs":['
    '{"find":"CO squared","replace":"carbon dioxide","reason":"CO2 mis-read"},'
    '{"find":"Buckley and Mott","replace":"Buckley and Mott twenty thirteen","reason":"year"}],'
    '"issues":[{"kind":"citation_error","severity":"low","location":"x","detail":"y",'
    '"suggestion":"z"}]}'
)


class _ScriptedLlm:
    """Prompt-aware fake: returns the writer plan for the writer prompt and a fixed auditor verdict
    for the auditor prompt (the stage now makes both kinds of call)."""

    def __init__(self, plan_json: str, verdict_json: str = '{"faithful": true}') -> None:
        self.plan_json = plan_json
        self.verdict_json = verdict_json
        self.writer_calls = 0
        self.audit_calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        if "ORIGINAL:" in prompt and "SPOKEN:" in prompt:  # the auditor prompt
            self.audit_calls += 1
            return self.verdict_json
        self.writer_calls += 1
        return self.plan_json


@pytest.mark.parametrize(
    "find,replace,safe",
    [
        ("CO squared", "carbon dioxide", True),  # pronunciation swap, no new facts
        ("mm", "millimeters", True),
        ("H two degrees", "water", True),
        # a leaked fragment ending "(two point nine)" -> announce; "Equation" is structural, and
        # the number is sourced from find, so this is safe
        ("equals mu and so on (two point nine)", "Equation two point nine", True),
        ("see the diagram", "see Figure three", False),  # but a NEW number is still fabrication
        ("Buckley and Mott", "Buckley and Mott twenty thirteen", False),  # fabricated year
        ("the first chapter", "the second chapter", False),  # fabricated ordinal
        ("conductance & Sack", "Scoffoni and Sack", False),  # fabricated name
        ("eight hundred four", "eight zero four", False),  # fabricated number-word
        ("same", "same", False),  # no-op
        ("x" * 200, "y", False),  # too large a span
    ],
)
def test_guard_blocks_fabrication(find: str, replace: str, safe: bool) -> None:
    assert is_safe_script_repair(find, replace) is safe


def test_parse_handles_garbage() -> None:
    assert parse_script_repair_plan("not json").is_empty()
    plan = parse_script_repair_plan(f"```json\n{_PLAN}\n```")
    assert len(plan.repairs) == 2 and len(plan.issues) == 1


def test_apply_preserves_block_ids_and_skips_unsafe() -> None:
    chunks = [
        Chunk(id="c1", text="the CO squared rate rose ", block_ids=["b1"], chapter=1),
        Chunk(id="c2", text="per Buckley and Mott here", block_ids=["b2"], chapter=1),
    ]
    plan = parse_script_repair_plan(_PLAN)
    applied, rejected = apply_script_repairs(chunks, plan.repairs)
    assert [a.find for a in applied] == ["CO squared"]  # safe one applied
    assert chunks[0].text == "the carbon dioxide rate rose " and chunks[0].block_ids == ["b1"]
    assert any(r.find == "Buckley and Mott" for r in rejected)  # fabrication blocked
    assert chunks[1].text == "per Buckley and Mott here"  # untouched


def test_apply_reports_not_found() -> None:
    chunks = [Chunk(id="c1", text="clean text", block_ids=["b1"])]
    _, rejected = apply_script_repairs(chunks, [ScriptRepair(find="absent", replace="present")])
    assert rejected and rejected[0].why == "not found in script"


def test_stage_mock_is_noop(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    doc = Document(
        meta=DocumentMeta(title="t"),
        script="the CO squared rate",
        chunks=[Chunk(id="c1", text="the CO squared rate", block_ids=["b1"])],
    )
    ScriptRepairStage().run(doc, ctx)
    assert doc.script == "the CO squared rate"  # mock LLM -> empty plan -> no-op
    assert ctx.script_repair_applied == []


def _doc() -> Document:
    text = "the CO squared rate per Buckley and Mott"
    return Document(
        meta=DocumentMeta(title="t"),
        script=text,
        chunks=[Chunk(id="c1", text=text, block_ids=["b"])],
    )


def test_stage_applies_safe_when_auditor_passes_and_caches(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _ScriptedLlm(_PLAN, verdict_json='{"faithful": true}')
    ctx.llm = fake

    doc = ScriptRepairStage().run(_doc(), ctx)
    # the safe edit passes guard + auditor and applies; the fabrication is guard-rejected
    assert "carbon dioxide" in (doc.script or "") and "CO squared" not in (doc.script or "")
    assert "Buckley and Mott" in (doc.script or "")
    assert len(ctx.script_repair_applied) == 1
    assert any("Buckley" in r.find for r in ctx.script_repair_rejected)
    calls_after_first = (fake.writer_calls, fake.audit_calls)
    ScriptRepairStage().run(_doc(), ctx)  # identical input -> every call cache-hits
    assert (fake.writer_calls, fake.audit_calls) == calls_after_first


def test_stage_auditor_vetoes_a_guard_passing_edit(tiny_ir_path: Path) -> None:
    # A claim flip ("increased" -> "decreased") adds no number/name, so the deterministic guard
    # passes it - but it changes meaning, so the auditor panel must veto it (fail-closed).
    plan = '{"repairs":[{"find":"the value increased","replace":"the value decreased"}]}'
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ctx.llm = _ScriptedLlm(plan, verdict_json='{"faithful": false, "reason": "claim flipped"}')
    doc = Document(
        meta=DocumentMeta(title="t"),
        script="we found the value increased here",
        chunks=[Chunk(id="c1", text="we found the value increased here", block_ids=["b"])],
    )
    ScriptRepairStage().run(doc, ctx)
    assert doc.script == "we found the value increased here"  # NOT applied
    assert ctx.script_repair_applied == []
    assert any(r.why.startswith("auditor:") for r in ctx.script_repair_rejected)


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(script_repair=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _ScriptedLlm(_PLAN)
    ctx.llm = fake
    doc = _doc()
    ScriptRepairStage().run(doc, ctx)
    assert fake.writer_calls == 0 and fake.audit_calls == 0
    assert doc.script == "the CO squared rate per Buckley and Mott"
