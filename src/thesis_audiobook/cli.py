"""Typer CLI. The composition root: the only place (besides adapters) that does I/O.

`run` drives the full pipeline; `--dry-run` is the no-call cost estimator and
`--preview` renders only the first chapter. The other subcommands are milestone stubs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from thesis_audiobook.adapters.anthropic_llm import AnthropicUnavailableError
from thesis_audiobook.adapters.elevenlabs_tts import ElevenLabsUnavailableError
from thesis_audiobook.adapters.ffmpeg_muxer import FfmpegUnavailableError
from thesis_audiobook.bootstrap import build_context
from thesis_audiobook.chunking import preview_chunks
from thesis_audiobook.config import Config, OutputMode, ParserBackend, profile_for
from thesis_audiobook.cost import estimate_cost
from thesis_audiobook.curate import PronunciationPlan
from thesis_audiobook.ir import Chunk, Document, DocumentMeta
from thesis_audiobook.linkage import citation_linkage
from thesis_audiobook.stages import build_default_pipeline
from thesis_audiobook.stages.assemble_audio import slugify

app = typer.Typer(
    add_completion=False,
    help="Convert a PhD thesis PDF into a navigable audiobook.",
)


_PARSER_HELP = "Parser backend: poppler (offline), marker, or mineru."
_LLM_HELP = (
    "Gloss/summary backend: mock (offline, free) or anthropic "
    "(real LLM via ANTHROPIC_API_KEY, costs money)."
)
_TTS_HELP = (
    "TTS backend: mock (offline, free, stand-in audio) or elevenlabs "
    "(real render + pronunciation publish + ffmpeg mux; needs the key and ffmpeg, costs money)."
)
_FORMAT_HELP = (
    "Audio output: m4b or mp4 (one chaptered file; mp4 plays everywhere) "
    "or mp3 (one file per chapter)."
)


def _validate_parser(name: str) -> ParserBackend:
    if name not in ("marker", "mineru", "poppler"):
        typer.echo(f"error: unknown parser {name!r}; choose poppler, marker, or mineru", err=True)
        raise typer.Exit(code=2)
    return name


def _validate_llm(name: str) -> bool:
    """Return True for the real Anthropic backend, False for the mock."""
    if name not in ("mock", "anthropic"):
        typer.echo(f"error: unknown llm {name!r}; choose mock or anthropic", err=True)
        raise typer.Exit(code=2)
    return name == "anthropic"


def _validate_tts(name: str) -> bool:
    """Return True for the real ElevenLabs backend, False for the mock."""
    if name not in ("mock", "elevenlabs"):
        typer.echo(f"error: unknown tts {name!r}; choose mock or elevenlabs", err=True)
        raise typer.Exit(code=2)
    return name == "elevenlabs"


def _validate_format(name: str) -> OutputMode:
    if name not in ("m4b", "mp4", "mp3"):
        typer.echo(f"error: unknown format {name!r}; choose m4b, mp4, or mp3", err=True)
        raise typer.Exit(code=2)
    return name


def _chunk_plan_summary(chunks: list[Chunk], limit: int) -> str:
    if not chunks:
        return "0 chunks"
    sizes = [len(chunk.text) for chunk in chunks]
    return (
        f"{len(chunks)} chunks (min {min(sizes)}, mean {sum(sizes) // len(sizes)}, "
        f"max {max(sizes)} chars; cap {limit})"
    )


def _write_review_artifacts(out: Path, doc: Document) -> tuple[Path, Path]:
    slug = slugify(doc.meta.title)
    script_path = out / f"{slug}.script.md"
    script_path.write_text(doc.script or "", encoding="utf-8")
    chunks_path = out / f"{slug}.chunks.json"
    chunks_path.write_text(
        json.dumps([chunk.model_dump() for chunk in doc.chunks], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return script_path, chunks_path


def _format_qa(plan: PronunciationPlan | None) -> str:
    """Render the curator's plan as a human-readable transparency report."""
    lines = ["# Pronunciation QA (LLM curator)", ""]
    # Notes alone still matter (is_empty ignores them): surface the curator's flagged
    # uncertainties even when it mapped nothing.
    if plan is None or (plan.is_empty() and not plan.notes):
        lines.append("Curator returned no entries (offline mock, or nothing to curate).")
        return "\n".join(lines) + "\n"

    def cell(value: str) -> str:
        return value.replace("|", "\\|")

    if plan.acronyms:
        lines += ["## Acronyms", "", "| acronym | first use | short form |", "|---|---|---|"]
        lines += [
            f"| {cell(a.acronym)} | {cell(a.first_use)} | {cell(a.short_form)} |"
            for a in plan.acronyms
        ]
        lines.append("")
    if plan.terms:
        lines += ["## Terms", "", "| term | spoken |", "|---|---|"]
        lines += [f"| {cell(t.term)} | {cell(t.spoken)} |" for t in plan.terms] + [""]
    if plan.notation:
        lines += ["## Notation", "", "| written | spoken |", "|---|---|"]
        lines += [f"| {cell(n.written)} | {cell(n.spoken)} |" for n in plan.notation] + [""]
    if plan.notes:
        lines += ["## Notes / flagged", ""] + [f"- {note}" for note in plan.notes]
    return "\n".join(lines) + "\n"


@app.command()
def run(
    input_pdf: Annotated[Path, typer.Argument(help="Path to the thesis PDF.")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="No external calls; estimate cost + show chunk plan.")
    ] = False,
    preview: Annotated[
        bool, typer.Option("--preview", help="Render only the first chapter.")
    ] = False,
    profile: Annotated[
        str, typer.Option(help="Listener profile: committee or general.")
    ] = "committee",
    parser: Annotated[str, typer.Option("--parser", help=_PARSER_HELP)] = "poppler",
    llm: Annotated[str, typer.Option("--llm", help=_LLM_HELP)] = "mock",
    tts: Annotated[str, typer.Option("--tts", help=_TTS_HELP)] = "mock",
    audio_format: Annotated[str, typer.Option("--format", help=_FORMAT_HELP)] = "m4b",
    voice: Annotated[
        str | None,
        typer.Option("--voice", help="ElevenLabs voice id (required for --tts elevenlabs)."),
    ] = None,
    no_curate: Annotated[
        bool, typer.Option("--no-curate", help="Skip the LLM pronunciation curator.")
    ] = False,
    seed: Annotated[int, typer.Option(help="Determinism seed.")] = 0,
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("out"),
    cache_dir: Annotated[Path, typer.Option(help="Content-addressed TTS cache directory.")] = Path(
        ".cache/tts"
    ),
) -> None:
    """Run the pipeline: parse -> script -> render -> assemble.

    Parsing is real (poppler offline, or marker/mineru + GROBID). LLM glosses and TTS are
    mocked by default; --llm anthropic and --tts elevenlabs switch on the real, billed
    services (the real render also needs ffmpeg). --dry-run estimates cost with no external
    calls; --preview renders only the first chapter.
    """
    if not input_pdf.exists():
        typer.echo(f"error: input PDF not found: {input_pdf}", err=True)
        raise typer.Exit(code=2)

    use_real_llm = _validate_llm(llm)
    use_real_tts = _validate_tts(tts)
    config = Config(
        profile=profile_for(profile),
        seed=seed,
        output_dir=str(out),
        cache_dir=str(cache_dir),
        parser_backend=_validate_parser(parser),
        output_mode=_validate_format(audio_format),
        curate=not no_curate,
    )
    if preview:
        # A preview renders with the cheap flash model, not the deliverable model.
        config.profile.model_id = config.profile.preview_model_id
    resolved_voice = voice or os.environ.get("ELEVENLABS_VOICE_ID")
    if resolved_voice:
        config.profile.voice_id = resolved_voice
    ctx = build_context(
        config,
        pdf_bytes=input_pdf.read_bytes(),
        log_enabled=False,
        # --dry-run makes zero external calls, so force the mocks even with --llm/--tts set
        # (the curator and gloss stages run before assemble_script).
        use_real_llm=use_real_llm and not dry_run,
        use_real_tts=use_real_tts and not dry_run,
    )
    pipeline = build_default_pipeline()
    seed_doc = Document(meta=DocumentMeta(title="(pending)"))
    out.mkdir(parents=True, exist_ok=True)

    if dry_run:
        # Stop before lexicon/tts/assemble, so no publish or render ever happens.
        doc = pipeline.run(seed_doc, ctx, to="assemble_script")
        _write_review_artifacts(out, doc)
        estimate = estimate_cost(doc.script or "", config.usd_per_character)
        typer.echo("Thesis-to-Audiobook  --dry-run (no external calls)")
        typer.echo(f"  title          : {doc.meta.title}")
        typer.echo(f"  profile        : {config.profile.name}")
        typer.echo(f"  script chars   : {estimate.characters}")
        typer.echo(f"  chunk plan     : {_chunk_plan_summary(doc.chunks, config.chunk_char_limit)}")
        typer.echo(f"  rate USD/char  : {estimate.usd_per_character}")
        typer.echo(f"  estimated USD  : {estimate.estimated_usd}")
        typer.echo(f"  note           : {estimate.note}")
        return

    if use_real_tts and config.profile.voice_id in (None, "", "mock-voice"):
        typer.echo(
            "error: --tts elevenlabs needs a real voice; pass --voice <id> or set "
            "ELEVENLABS_VOICE_ID",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        if preview:
            doc = pipeline.run(seed_doc, ctx, to="lexicon")
            doc.chunks = preview_chunks(doc.chunks)
            doc = pipeline.run(doc, ctx, frm="tts")
        else:
            doc = pipeline.run(seed_doc, ctx)
    except (
        AnthropicUnavailableError,
        ElevenLabsUnavailableError,
        FfmpegUnavailableError,
    ) as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(code=2) from error

    slug = slugify(doc.meta.title)
    script_path, chunks_path = _write_review_artifacts(out, doc)
    audio_paths: list[Path] = []
    for blob in ctx.audio_outputs:
        path = out / blob.filename
        path.write_bytes(blob.data)
        audio_paths.append(path)
    provenance_path = out / f"{slug}.provenance.json"
    if ctx.provenance is not None:
        provenance_path.write_text(ctx.provenance.model_dump_json(indent=2), encoding="utf-8")
    qa_path = out / f"{slug}.qa.md"
    qa_path.write_text(_format_qa(ctx.pronunciation_plan), encoding="utf-8")

    estimate = estimate_cost(doc.script or "", config.usd_per_character)
    llm_backend = "anthropic (real)" if use_real_llm else "mock"
    tts_backend = "elevenlabs (real)" if use_real_tts else "mock"
    total_bytes = sum(len(blob.data) for blob in ctx.audio_outputs)
    audio_list = ", ".join(str(path) for path in audio_paths)
    audio_label = f"audio [{config.output_mode}, {ctx.chapter_count} ch]"
    scope = "  (preview: first chapter)" if preview else ""
    typer.echo("Thesis-to-Audiobook  (M4: render + assembly)")
    typer.echo(f"  input PDF         : {input_pdf}")
    typer.echo(f"  parser/llm/tts    : {config.parser_backend} / {llm_backend} / {tts_backend}")
    typer.echo(f"  profile           : {config.profile.name}{scope}")
    typer.echo(f"  chunks            : {len(doc.chunks)}")
    typer.echo(f"  script chars      : {estimate.characters}")
    typer.echo(f"  reviewable script : {script_path}  (Gate B artifact)")
    typer.echo(f"  chunk plan        : {chunks_path}")
    typer.echo(f"  {audio_label:<18}: {audio_list} ({total_bytes} bytes)")
    typer.echo(f"  provenance        : {provenance_path}")
    typer.echo(f"  pronunciation qa  : {qa_path}")
    typer.echo("  Gate A warnings:")
    typer.echo(ctx.warnings.report())
    if use_real_tts:
        typer.echo("  Real ElevenLabs render + ffmpeg mux were used (billed).")
    elif use_real_llm:
        typer.echo("  Real Anthropic glosses were used (billed); TTS mocked.")
    else:
        typer.echo("  no paid calls were made (LLM/TTS mocked).")


@app.command()
def parse(
    input_pdf: Annotated[Path, typer.Argument(help="Path to the thesis PDF.")],
    out_ir: Annotated[Path, typer.Option("--out", "-o", help="Where to write the IR JSON.")] = Path(
        "out/ir.json"
    ),
    parser: Annotated[str, typer.Option("--parser", help=_PARSER_HELP)] = "poppler",
) -> None:
    """Parse a PDF to the cleaned IR (ingest + build_ir), then report structure."""
    if not input_pdf.exists():
        typer.echo(f"error: input PDF not found: {input_pdf}", err=True)
        raise typer.Exit(code=2)

    config = Config(parser_backend=_validate_parser(parser))
    ctx = build_context(config, pdf_bytes=input_pdf.read_bytes(), log_enabled=False)
    doc = build_default_pipeline().run(
        Document(meta=DocumentMeta(title="(pending)")), ctx, frm="ingest", to="build_ir"
    )

    out_ir.parent.mkdir(parents=True, exist_ok=True)
    out_ir.write_text(doc.model_dump_json(indent=2), encoding="utf-8")

    rate, resolved, unresolved = citation_linkage(doc)
    counts: dict[str, int] = {}
    for block in doc.blocks:
        counts[block.type.value] = counts.get(block.type.value, 0) + 1

    typer.echo(f"parsed {input_pdf} with {parser}")
    typer.echo(f"  IR written       : {out_ir}")
    typer.echo(f"  title            : {doc.meta.title}")
    typer.echo(f"  blocks           : {len(doc.blocks)}  {counts}")
    typer.echo(f"  bibliography      : {len(doc.bibliography)} entries")
    typer.echo(
        f"  citation linkage : {rate:.0%} ({len(resolved)}/{len(resolved) + len(unresolved)} "
        f"markers); unresolved: {unresolved or 'none'}"
    )
    typer.echo("  Gate A warnings:")
    typer.echo(ctx.warnings.report())


def _use_run(verb: str) -> None:
    typer.echo(
        f"'{verb}' is not a separate command in this build. The whole pipeline "
        "(parse -> script -> render -> assemble) runs through `audiobook run`; see "
        "`audiobook run --help`.",
        err=True,
    )
    raise typer.Exit(code=2)


@app.command()
def script(ir_json: Annotated[Path, typer.Argument(help="Path to an IR JSON file.")]) -> None:
    """Superseded by `audiobook run` (which produces the Gate B script + chunk plan)."""
    _use_run("script")


@app.command()
def render(script_md: Annotated[Path, typer.Argument(help="Path to a script file.")]) -> None:
    """Superseded by `audiobook run --tts elevenlabs` (parse through render in one pass)."""
    _use_run("render")


@app.command()
def assemble(audio_dir: Annotated[Path, typer.Argument(help="Directory of audio chunks.")]) -> None:
    """Superseded by `audiobook run` (assembly + provenance are part of the pipeline)."""
    _use_run("assemble")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
