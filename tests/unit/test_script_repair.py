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


class _FakeLlm:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return self.response


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


def test_stage_applies_safe_repairs_and_caches(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_PLAN)
    ctx.llm = fake

    def fresh() -> Document:
        return Document(
            meta=DocumentMeta(title="t"),
            script="the CO squared rate per Buckley and Mott",
            chunks=[
                Chunk(id="c1", text="the CO squared rate per Buckley and Mott", block_ids=["b"])
            ],
        )

    doc = ScriptRepairStage().run(fresh(), ctx)
    assert "carbon dioxide" in (doc.script or "") and "CO squared" not in (doc.script or "")
    assert "Buckley and Mott" in (doc.script or "")  # fabrication left in place
    assert len(ctx.script_repair_applied) == 1 and len(ctx.script_repair_rejected) == 1
    ScriptRepairStage().run(fresh(), ctx)  # same script -> cached, no second call
    assert fake.calls == 1


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(script_repair=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_PLAN)
    ctx.llm = fake
    doc = Document(
        meta=DocumentMeta(title="t"),
        script="the CO squared rate",
        chunks=[Chunk(id="c1", text="the CO squared rate", block_ids=["b1"])],
    )
    ScriptRepairStage().run(doc, ctx)
    assert fake.calls == 0 and doc.script == "the CO squared rate"
