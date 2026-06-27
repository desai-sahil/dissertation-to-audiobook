from __future__ import annotations

from pathlib import Path

import pytest

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.stages.structurer import StructurerStage
from thesis_audiobook.structurer import (
    apply_structure,
    build_outline,
    parse_structure_plan,
    suspicious_blocks,
)


class _FakeLlm:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return self.response


@pytest.mark.parametrize(
    "text,suspicious",
    [
        # --- must be flagged (code / non-narratable), several from the red-team ---
        ("i m p o rt p a n d a s a s pd", True),  # parser-shredded code
        ("import numpy as np", True),
        ("plt.figure(figsize=(6, 4))", True),
        ("def calibrate(data):", True),
        ("```python", True),
        ("S e r i e s C r e at e d by S h o r t Cut", True),  # spaced garble
        ("df = pd.read_csv(path)", True),  # assign + method-call
        ("int main(int argc, char **argv) {", True),  # C: call + brace
        ("SELECT a.id FROM samples a JOIN reads b ON a.id = b.sample_id", True),  # SQL
        ('{"gene": "RBCS1", "fold_change": 2.4, "padj": 0.01}', True),  # JSON
        ("cat reads.fq | grep -c x > counts.txt", True),  # shell pipe + flag + redirect
        ("learning_rate: 0.001\nbatch_size: 32\noptimizer: adam", True),  # config block
        ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk", True),  # base64 blob
        ("Logger,Ch1,Ch2,Ch3,2023-01-01T00:00,21.4,55.2,1013", True),  # CSV row
        ("Coeff: 0.998 1.002 0.997 -0.011 1.004 0.996", True),  # number dump
        # --- must NOT be flagged (genuine prose, even when it mentions code/chemistry) ---
        ("The stomata regulate transpiration under drought stress.", False),
        ("We measured 5 ml of 0.1 M NaCl at 25 C for 30 minutes.", False),
        ("As shown in Figure 1.1, the gradient steepens toward the tip.", False),
        ("Background subtraction relied on np.median over the dark frames.", False),
        ("Peaks were detected with scipy.signal and their areas integrated.", False),
        ("All analyses used the lme4 and emmeans packages in R version 4.2.1.", False),
        ("Catalase drives the disproportionation 2 H2O2 -> 2 H2O + O2 here.", False),
    ],
)
def test_triage_flags_code_not_prose(text: str, suspicious: bool) -> None:
    block = Block(id="b", type=BlockType.paragraph, text=text)
    assert bool(suspicious_blocks([block])) is suspicious


def test_triage_only_considers_paragraphs() -> None:
    # a heading/reference already typed by the cheap pass is trusted, not re-sent
    blocks = [
        Block(id="h", type=BlockType.heading, text="import of water across the membrane"),
        Block(id="p", type=BlockType.paragraph, text="def f(): return 1"),
    ]
    assert [b.id for b in suspicious_blocks(blocks)] == ["p"]


def test_parse_handles_garbage() -> None:
    assert parse_structure_plan("not json").is_empty()
    plan = parse_structure_plan('{"labels":[{"id":"m2","kind":"code"}]}')
    assert len(plan.labels) == 1


def test_apply_sets_types_logs_changes_and_ignores_unknowns() -> None:
    blocks = [
        Block(id="m1", type=BlockType.paragraph, text="prose"),
        Block(id="m2", type=BlockType.paragraph, text="i m p o rt"),
        Block(id="m3", type=BlockType.paragraph, text="ref"),
    ]
    plan = parse_structure_plan(
        '{"labels":[{"id":"m2","kind":"code"},{"id":"m3","kind":"reference"},'
        '{"id":"m1","kind":"boguskind"},{"id":"absent","kind":"code"}]}'
    )
    changes = apply_structure(blocks, plan)
    kinds = {b.id: b.type for b in blocks}
    assert kinds["m2"] is BlockType.code and kinds["m3"] is BlockType.reference_list
    assert kinds["m1"] is BlockType.paragraph  # unknown kind ignored
    assert {c.id for c in changes} == {"m2", "m3"}  # only real changes logged; absent id skipped


def _doc_with_code() -> Document:
    return Document(
        meta=DocumentMeta(title="t"),
        blocks=[
            Block(id="m1", type=BlockType.paragraph, text="A clean sentence of body prose here."),
            Block(id="m2", type=BlockType.paragraph, text="i m p o rt p a n d a s a s pd"),
        ],
    )


def test_stage_sends_only_suspects_and_reclassifies(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm('{"labels":[{"id":"m2","kind":"code"}]}')
    ctx.llm = fake
    doc = _doc_with_code()
    StructurerStage().run(doc, ctx)
    kinds = {b.id: b.type for b in doc.blocks}
    assert kinds["m2"] is BlockType.code and kinds["m1"] is BlockType.paragraph
    assert len(ctx.reclassifications) == 1
    assert any("reclassified" in w.reason for w in ctx.warnings.items)
    StructurerStage().run(_doc_with_code(), ctx)  # same suspects -> cached
    assert fake.calls == 1


def test_stage_no_suspects_makes_no_llm_call(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm('{"labels":[{"id":"m1","kind":"code"}]}')
    ctx.llm = fake
    doc = Document(
        meta=DocumentMeta(title="t"),
        blocks=[Block(id="m1", type=BlockType.paragraph, text="All clean prose, nothing unusual.")],
    )
    StructurerStage().run(doc, ctx)
    assert fake.calls == 0  # nothing suspicious -> the model is never called
    assert doc.blocks[0].type is BlockType.paragraph and ctx.reclassifications == []


def test_stage_mock_is_noop(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    doc = _doc_with_code()
    StructurerStage().run(doc, ctx)  # suspect exists, but mock LLM -> empty plan -> no change
    assert all(b.type is BlockType.paragraph for b in doc.blocks)
    assert ctx.reclassifications == []


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(structurer=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm('{"labels":[{"id":"m2","kind":"code"}]}')
    ctx.llm = fake
    doc = _doc_with_code()
    StructurerStage().run(doc, ctx)
    assert fake.calls == 0 and all(b.type is BlockType.paragraph for b in doc.blocks)


def test_outline_uses_block_ids_and_types() -> None:
    outline = build_outline(_doc_with_code().blocks)
    assert "m2 | paragraph | i m p o rt" in outline and outline.count("\n") == 1
