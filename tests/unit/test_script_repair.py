from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Chunk, Document, DocumentMeta
from thesis_audiobook.script_repair import (
    ScriptRepair,
    apply_one,
    candidate_repairs,
    parse_script_repair_plan,
)
from thesis_audiobook.stages.script_repair import ScriptRepairStage


def test_candidate_repairs_copyedit_dispatch_by_kind() -> None:
    script = "the responce curve rose to 0.5 here and is not flat overall."
    repairs = [
        ScriptRepair(find="responce", replace="response", reason="typo", kind="spelling"),
        ScriptRepair(find="0.5 here", replace="0.9 here", reason="num", kind="grammar"),  # guard
        ScriptRepair(find="is not flat", replace="is flat", reason="x", kind="grammar"),  # guard
        ScriptRepair(find="rose to 0.5", replace="rose to 0.5 now", reason="d", kind="data"),
    ]
    cands, rej = candidate_repairs(script, repairs, copyedit=True)
    kept = {c.find for c in cands}
    assert "responce" in kept  # spelling typo passes the copy-edit guard
    assert "0.5 here" not in kept  # number change blocked
    assert "is not flat" not in kept  # negation drop blocked
    assert any(r.find == "rose to 0.5" and "flag only" in r.why for r in rej)  # data never applied


def test_candidate_repairs_as_written_blocks_author_but_keeps_notation() -> None:
    cands, rej = candidate_repairs(
        "the responce curve",
        [ScriptRepair(find="responce", replace="response", kind="spelling")],
        copyedit=False,
    )
    assert not cands and any("--as-written" in r.why for r in rej)
    cands, _ = candidate_repairs(
        "say cm now",
        [ScriptRepair(find="cm", replace="centimeters", kind="notation")],
        copyedit=False,
    )
    assert cands and cands[0].replace == "centimeters"  # notation still applies as-written


_PLAN = (
    '{"summary":"notation fixes","repairs":['
    '{"find":"ten cm deep","replace":"ten centimeters deep","reason":"unit"},'
    '{"find":"absent phrase","replace":"whatever","reason":"not in script"}],'
    '"issues":[{"kind":"other","severity":"low","location":"x","detail":"y","suggestion":"z"}]}'
)


class _ScriptedLlm:
    """Prompt-aware fake: returns the writer plan for the writer prompt (the stage makes only the
    one writer call per round now - no auditor)."""

    def __init__(self, plan_json: str) -> None:
        self.plan_json = plan_json
        self.writer_calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.writer_calls += 1
        return self.plan_json


def test_tidy_punctuation_collapses_doubled_commas() -> None:
    from thesis_audiobook.stages.script_repair import tidy_punctuation

    # the ",," a too-aggressive edit can leave (parens rewritten as commas next to an existing one)
    assert tidy_punctuation("temperature,, solar") == "temperature, solar"
    assert tidy_punctuation("room temperature, H M P sixty, Vaisala,, solar") == (
        "room temperature, H M P sixty, Vaisala, solar"
    )
    assert tidy_punctuation("clean, normal text") == "clean, normal text"  # no-op on clean text


def test_apply_one_only_matches_whole_tokens() -> None:
    # the regression that prompted this design: a bare unit edit must NOT rewrite inside a word.
    chunks = [Chunk(id="c1", text="the committee saw five mm of growth", block_ids=["b1"])]
    count = apply_one(chunks, ScriptRepair(find="mm", replace="millimeters"))
    assert count == 1
    assert chunks[0].text == "the committee saw five millimeters of growth"  # committee untouched


def test_apply_one_preserves_block_ids_all_occurrences() -> None:
    chunks = [
        Chunk(id="c1", text="held at ten cm then twenty cm", block_ids=["b1"], chapter=1),
        Chunk(id="c2", text="and thirty cm later", block_ids=["b2"], chapter=1),
    ]
    count = apply_one(chunks, ScriptRepair(find="cm", replace="centimeters"))
    assert count == 3
    assert chunks[0].text == "held at ten centimeters then twenty centimeters"
    assert chunks[0].block_ids == ["b1"] and chunks[1].block_ids == ["b2"]


def test_candidate_repairs_keeps_locatable_drops_unfindable() -> None:
    script = "the sample at ten cm deep"
    repairs = [
        ScriptRepair(find="ten cm deep", replace="ten centimeters deep"),
        ScriptRepair(find="absent phrase", replace="x"),
        ScriptRepair(find="same", replace="same"),  # no-op
    ]
    candidates, rejected = candidate_repairs(script, repairs)
    assert [c.find for c in candidates] == ["ten cm deep"]
    whys = {r.find: r.why for r in rejected}
    assert whys["absent phrase"] == "not found in script"
    assert "no-op" in whys["same"]


def test_parse_handles_garbage() -> None:
    assert parse_script_repair_plan("not json").is_empty()
    plan = parse_script_repair_plan(f"```json\n{_PLAN}\n```")
    assert len(plan.repairs) == 2 and len(plan.issues) == 1


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
    text = "the sample at ten cm deep, recorded by the committee"
    return Document(
        meta=DocumentMeta(title="t"),
        script=text,
        chunks=[Chunk(id="c1", text=text, block_ids=["b"])],
    )


def test_stage_applies_notation_edit_and_caches(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _ScriptedLlm(_PLAN)
    ctx.llm = fake

    doc = ScriptRepairStage().run(_doc(), ctx)
    assert "ten centimeters deep" in (doc.script or "")
    assert "committee" in (doc.script or "")  # whole-token apply left the word intact
    assert len(ctx.script_repair_applied) == 1
    assert any(r.find == "absent phrase" for r in ctx.script_repair_rejected)
    calls_after_first = fake.writer_calls
    ScriptRepairStage().run(_doc(), ctx)  # identical input -> writer call cache-hits
    assert fake.writer_calls == calls_after_first


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(script_repair=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _ScriptedLlm(_PLAN)
    ctx.llm = fake
    doc = _doc()
    ScriptRepairStage().run(doc, ctx)
    assert fake.writer_calls == 0
    assert doc.script == "the sample at ten cm deep, recorded by the committee"
