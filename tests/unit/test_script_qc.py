from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.cli import app
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Document, DocumentMeta
from thesis_audiobook.script_qc import build_script_qc_prompt, parse_script_qc, render_script_qc_md
from thesis_audiobook.stages.script_qc import ScriptQcStage

runner = CliRunner()

_REPORT = (
    '{"summary":"Mostly ready.","issues":['
    '{"kind":"raw_latex","severity":"high","location":"$\\\\psi$","detail":"raw LaTeX leaked",'
    '"suggestion":"fix clean_markup"},'
    '{"kind":"mispronunciation","severity":"low","location":"gs","detail":"minor",'
    '"suggestion":"ok"}]}'
)


class _FakeLlm:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None):
        self.calls += 1
        return self.response


def test_prompt_includes_script_and_parse_handles_garbage() -> None:
    assert "Some narration." in build_script_qc_prompt("Some narration.")
    report = parse_script_qc(f"```json\n{_REPORT}\n```")
    assert len(report.issues) == 2
    assert len(report.high_severity()) == 1 and report.high_severity()[0].kind == "raw_latex"
    assert parse_script_qc("a mock gloss for input zz").is_empty()


def test_render_sorts_and_handles_empty() -> None:
    assert "No red flags" in render_script_qc_md(parse_script_qc("not json"))
    md = render_script_qc_md(parse_script_qc(_REPORT))
    assert "high-severity" in md and md.index("raw_latex") < md.index("mispronunciation")


def test_stage_mock_is_noop(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    doc = Document(meta=DocumentMeta(title="t"), script="Some clean narration script.")
    ScriptQcStage().run(doc, ctx)
    assert ctx.script_qc_report is not None and ctx.script_qc_report.is_empty()


def test_stage_caches_and_flags(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_REPORT)
    ctx.llm = fake
    doc = Document(meta=DocumentMeta(title="t"), script="A script with $\\psi$ leaked.")
    ScriptQcStage().run(doc, ctx)
    assert ctx.script_qc_report is not None and len(ctx.script_qc_report.high_severity()) == 1
    # same script -> cached, no second call
    ScriptQcStage().run(
        Document(meta=DocumentMeta(title="t"), script="A script with $\\psi$ leaked."), ctx
    )
    assert fake.calls == 1


def test_stage_disabled_skips(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(script_qc=False), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    fake = _FakeLlm(_REPORT)
    ctx.llm = fake
    ScriptQcStage().run(Document(meta=DocumentMeta(title="t"), script="x"), ctx)
    assert fake.calls == 0 and ctx.script_qc_report is None


def test_cli_run_shows_phases_and_writes_qc_artifact(sample_pdf: Path, tmp_path: Path) -> None:
    import shutil

    if shutil.which("pdftotext") is None:
        return  # poppler not installed in this env
    result = runner.invoke(
        app,
        [
            "run",
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
