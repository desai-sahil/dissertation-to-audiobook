from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.cli import app
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Chunk, Document, DocumentMeta
from thesis_audiobook.qc_fix import build_qc_fix_prompt
from thesis_audiobook.script_qc import (
    build_script_qc_prompt,
    found_verbatim,
    keep_locatable,
    parse_script_qc,
    render_script_qc_md,
)
from thesis_audiobook.stages.script_qc import ScriptQcStage

runner = CliRunner()

_REPORT = (
    '{"summary":"Mostly ready.","issues":['
    '{"kind":"raw_latex","severity":"high","location":"$\\\\psi$","detail":"raw LaTeX leaked",'
    '"suggestion":"fix clean_markup"},'
    '{"kind":"mispronunciation","severity":"low","location":"gs","detail":"minor",'
    '"suggestion":"ok"}]}'
)
_CLEAN = '{"summary":"Ready.","issues":[]}'
_FIX = '{"repairs":[{"find":"$\\\\psi$","replace":"psi","reason":"raw latex"}]}'


class _FakeLlm:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return self.response


class _AuditConfirm:
    """Opus stand-in: flags on the first sweep (audit), clean on the second (confirm)."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return _REPORT if self.calls == 1 else _CLEAN


def _doc(script: str) -> Document:
    return Document(
        meta=DocumentMeta(title="t"),
        script=script,
        chunks=[Chunk(id="c1", text=script, block_ids=["b"])],
    )


def test_prompt_includes_script_and_parse_handles_garbage() -> None:
    assert "Some narration." in build_script_qc_prompt("Some narration.")
    report = parse_script_qc(f"```json\n{_REPORT}\n```")
    assert len(report.issues) == 2
    assert len(report.high_severity()) == 1 and report.high_severity()[0].kind == "raw_latex"
    assert parse_script_qc("a mock gloss for input zz").is_empty()


def test_qc_fix_prompt_lists_flags() -> None:
    report = parse_script_qc(_REPORT)
    prompt = build_qc_fix_prompt("the script", report.issues)
    assert "find/replace edit" in prompt and "raw LaTeX leaked" in prompt


def test_render_sorts_and_handles_empty() -> None:
    assert "No red flags" in render_script_qc_md(parse_script_qc("not json"))
    md = render_script_qc_md(parse_script_qc(_REPORT))
    assert "high-severity" in md and md.index("raw_latex") < md.index("mispronunciation")


def test_found_verbatim_normalizes_whitespace() -> None:
    script = "the Stroock Group. The micro-tensiometer was used."
    assert found_verbatim("Stroock Group. The micro-tensiometer", script)
    assert found_verbatim("Stroock   Group.\nThe micro-tensiometer", script)  # ws-normalized
    assert not found_verbatim("we refer to several studies", script)  # paraphrased / not present
    assert not found_verbatim("", script)  # empty location is unlocatable


def test_found_verbatim_tolerates_cosmetic_drift() -> None:
    # A real HIGH flag must still locate (and so still block the gate) when the model quotes it with
    # only cosmetic drift; otherwise a broken render slips past. (All four were review-found drops.)
    assert found_verbatim(
        "\\frac{a}{b} sign.", "the ratio \\frac{a}{b} sign drives it"
    )  # tr. punct
    assert found_verbatim("‘C o e f f’", "the value 'C o e f f' appears")  # smart quotes
    assert found_verbatim("As shown in.", "as shown in. The next sentence")  # leading-cap
    assert found_verbatim("with increasing", "rate increased withincreasing light")  # fusion
    # a genuine paraphrase still does NOT locate -> still dropped
    assert not found_verbatim("we refer to several studies", "a clean sentence about leaves")


def test_keep_locatable_drops_phantom_and_notes_it() -> None:
    script = "published by the Stroock Group. The micro-tensiometer was used here."
    report = parse_script_qc(
        '{"summary":"x","issues":['
        '{"kind":"citation_error","severity":"high","location":"the Stroock Group. The micro-'
        'tensiometer","detail":"real","suggestion":""},'
        '{"kind":"truncation","severity":"high","location":"we refer to several studies",'
        '"detail":"phantom","suggestion":""}]}'
    )
    kept = keep_locatable(report, script)
    assert [i.detail for i in kept.issues] == ["real"]  # the hallucinated location is dropped
    assert kept.summary.startswith("x") and "dropped as unlocatable" in kept.summary


def test_stage_mock_is_noop(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ScriptQcStage().run(_doc("Some clean narration script."), ctx)
    assert ctx.script_qc_report is not None and ctx.script_qc_report.is_empty()


def test_loop_audits_fixes_then_confirms(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    opus = _AuditConfirm()  # Opus: audit (flags) then confirm (clean)
    sonnet = _FakeLlm(_FIX)  # Sonnet: the one fix pass
    ctx.verifier_llm = opus
    ctx.llm = sonnet
    doc = _doc("A script with $\\psi$ leaked.")
    ScriptQcStage().run(doc, ctx)
    assert opus.calls == 2 and sonnet.calls == 1  # Opus audit+confirm, one Sonnet fix
    assert "psi leaked" in (doc.script or "") and "$" not in (doc.script or "")  # fix applied
    assert ctx.script_qc_report is not None and ctx.script_qc_report.issues == []  # confirm clean
    assert any(a.find == "$\\psi$" for a in ctx.script_repair_applied)  # logged for the ledger


def test_loop_is_cached(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    opus, sonnet = _AuditConfirm(), _FakeLlm(_FIX)
    ctx.verifier_llm, ctx.llm = opus, sonnet
    ScriptQcStage().run(_doc("A script with $\\psi$ leaked."), ctx)
    ScriptQcStage().run(_doc("A script with $\\psi$ leaked."), ctx)  # identical -> all cache-hits
    assert opus.calls == 2 and sonnet.calls == 1  # no new calls on the 2nd run


def test_no_qc_loop_audits_only(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(qc_loop=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    sonnet = _FakeLlm(_REPORT)  # read-only audit runs on the cheap pipeline model
    opus = _FakeLlm(_CLEAN)
    ctx.llm, ctx.verifier_llm = sonnet, opus
    ScriptQcStage().run(_doc("A script with $\\psi$ leaked."), ctx)
    assert sonnet.calls == 1 and opus.calls == 0  # audit only, no fix/confirm
    assert ctx.script_qc_report is not None and len(ctx.script_qc_report.high_severity()) == 1


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(script_qc=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_REPORT)
    ctx.llm = fake
    ScriptQcStage().run(_doc("x"), ctx)
    assert fake.calls == 0 and ctx.script_qc_report is None


def test_cli_run_shows_phases_and_writes_qc_artifact(sample_pdf: Path, tmp_path: Path) -> None:
    import shutil

    if shutil.which("pdftotext") is None:
        return  # poppler not installed in this env
    result = runner.invoke(
        app,
        [
            "run-v1",
            str(sample_pdf),
            "--parser",
            "poppler",
            "--tts",
            "mock",
            "--out",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "c"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Phase 3" in result.output and "Phase 4" in result.output and "Phase 5" in result.output
    assert list(tmp_path.glob("*.script-qc.md"))  # phase-4 artifact written
