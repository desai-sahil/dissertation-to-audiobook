"""Typer CLI. The composition root: the only place (besides adapters) that does I/O.

`run` drives the full pipeline; `--dry-run` is the no-call cost estimator and
`--preview` renders only the first chapter. The other subcommands are milestone stubs.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Annotated

import typer

from thesis_audiobook.adapters.anthropic_llm import AnthropicUnavailableError
from thesis_audiobook.adapters.elevenlabs_tts import ElevenLabsUnavailableError
from thesis_audiobook.adapters.ffmpeg_muxer import FfmpegUnavailableError
from thesis_audiobook.bootstrap import build_context
from thesis_audiobook.cartographer import render_structure_md
from thesis_audiobook.chunking import preview_chunks
from thesis_audiobook.config import Config, OutputMode, ParserBackend, profile_for
from thesis_audiobook.context import Context
from thesis_audiobook.cost import estimate_cost
from thesis_audiobook.curate import PronunciationPlan
from thesis_audiobook.extraction_qc import (
    EXTRACTION_QC_MAX_TOKENS,
    EXTRACTION_QC_SYSTEM,
    EXTRACTION_QC_VERSION,
    ExtractionQCReport,
    build_qc_prompt,
    parse_qc,
    render_qc_md,
)
from thesis_audiobook.ir import Chunk, Document, DocumentMeta, StructureMap
from thesis_audiobook.linkage import citation_linkage
from thesis_audiobook.stages import build_default_pipeline
from thesis_audiobook.stages.assemble_audio import slugify

app = typer.Typer(
    add_completion=False,
    help="Convert a PhD thesis PDF into a navigable audiobook.",
)


_PARSER_HELP = "Parser backend: poppler (offline), marker, mineru, or markdown (pre-parsed file)."
_MARKDOWN_HELP = (
    "Ingest a pre-parsed markdown file (from a standalone Marker/MinerU run) as the source, "
    "instead of parsing the PDF here. Sets --parser markdown. Best structure for complex theses."
)
_LLM_HELP = (
    "Gloss/summary backend: mock (offline, free) or anthropic "
    "(real LLM via ANTHROPIC_API_KEY, costs money)."
)
_TTS_HELP = (
    "TTS backend: mock (offline, free, stand-in audio) or elevenlabs "
    "(real render + pronunciation publish + ffmpeg mux; needs the key and ffmpeg, costs money)."
)
_FORMAT_HELP = (
    "Audio output: m4b or mp4 (one chaptered file; mp4 plays everywhere). "
    "A single whole-book mp3 is always emitted alongside; mp3 mode emits only that."
)
_COVER_HELP = (
    "Cover image (PNG/JPEG). The mp4 shows it for the whole runtime; the m4b/mp3 embed "
    "it as album art. Defaults to cover/cover01.png; omit the file to render audio-only."
)


def _validate_parser(name: str) -> ParserBackend:
    if name not in ("marker", "mineru", "poppler", "markdown"):
        typer.echo(
            f"error: unknown parser {name!r}; choose poppler, marker, mineru, or markdown",
            err=True,
        )
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


_DEFAULT_COVER = Path("cover/cover01.png")


def _resolve_cover(cover: Path | None) -> tuple[bytes | None, str]:
    """Resolve the cover image to embed, or (None, reason) to render audio-only.

    A missing default cover is silent (the user opted out by not adding one); a missing
    *explicitly named* cover is a likely typo, so we warn but still render audio-only
    rather than abort a long render.
    """
    path = cover if cover is not None else _DEFAULT_COVER
    if path.exists():
        return path.read_bytes(), str(path)
    if cover is not None:
        typer.echo(f"warning: cover not found: {path}; rendering without cover art", err=True)
        return None, "none (file not found)"
    return None, f"none (no {_DEFAULT_COVER})"


def _write_structure_md(
    out: Path, doc: Document, structure_map: StructureMap | None, *, include_appendices: bool
) -> Path:
    """Write the cartographer's structure map for the pre-spend review (Gate A artifact)."""
    path = out / f"{slugify(doc.meta.title)}.structure.md"
    path.write_text(
        render_structure_md(
            structure_map or StructureMap(), doc, include_appendices=include_appendices
        ),
        encoding="utf-8",
    )
    return path


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
    if plan.dehyphenations:
        lines += ["## De-hyphenations", "", "| broken | fixed |", "|---|---|"]
        lines += [f"| {cell(d.broken)} | {cell(d.fixed)} |" for d in plan.dehyphenations] + [""]
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
    markdown: Annotated[Path | None, typer.Option("--markdown", help=_MARKDOWN_HELP)] = None,
    llm: Annotated[str, typer.Option("--llm", help=_LLM_HELP)] = "mock",
    tts: Annotated[str, typer.Option("--tts", help=_TTS_HELP)] = "mock",
    audio_format: Annotated[str, typer.Option("--format", help=_FORMAT_HELP)] = "m4b",
    cover: Annotated[Path | None, typer.Option("--cover", help=_COVER_HELP)] = None,
    voice: Annotated[
        str | None,
        typer.Option("--voice", help="ElevenLabs voice id (required for --tts elevenlabs)."),
    ] = None,
    no_curate: Annotated[
        bool, typer.Option("--no-curate", help="Skip the LLM pronunciation curator.")
    ] = False,
    no_structure_eval: Annotated[
        bool,
        typer.Option(
            "--no-structure-eval",
            help="Skip the LLM thesis cartographer (front/back matter + appendix detection).",
        ),
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
        structure_eval=not no_structure_eval,
    )
    if markdown is not None:
        if not markdown.exists():
            typer.echo(f"error: markdown file not found: {markdown}", err=True)
            raise typer.Exit(code=2)
        # Ingest the pre-parsed markdown instead of parsing the PDF here.
        config.parser_backend = "markdown"
        config.markdown_path = str(markdown)
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
        structure_path = _write_structure_md(
            out, doc, ctx.structure_map, include_appendices=config.profile.include_appendices
        )
        estimate = estimate_cost(doc.script or "", config.usd_per_character)
        typer.echo("Thesis-to-Audiobook  --dry-run (no external calls)")
        typer.echo(f"  title          : {doc.meta.title}")
        typer.echo(f"  profile        : {config.profile.name}")
        typer.echo(f"  script chars   : {estimate.characters}")
        typer.echo(f"  chunk plan     : {_chunk_plan_summary(doc.chunks, config.chunk_char_limit)}")
        typer.echo(f"  structure map  : {structure_path}")
        typer.echo(f"  rate USD/char  : {estimate.usd_per_character}")
        typer.echo(f"  estimated USD  : {estimate.estimated_usd}")
        typer.echo(f"  note           : {estimate.note}")
        return

    if use_real_llm and not os.environ.get("ANTHROPIC_API_KEY"):
        typer.echo(
            "error: --llm anthropic needs ANTHROPIC_API_KEY set in this shell "
            "(used by the equation glosses and the pronunciation curator).",
            err=True,
        )
        raise typer.Exit(code=2)
    if use_real_tts and not (
        os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_LABS_API_KEY")
    ):
        typer.echo("error: --tts elevenlabs needs ELEVENLABS_API_KEY set in this shell.", err=True)
        raise typer.Exit(code=2)
    if use_real_tts and config.profile.voice_id in (None, "", "mock-voice"):
        typer.echo(
            "error: --tts elevenlabs needs a real voice; pass --voice <id> or set "
            "ELEVENLABS_VOICE_ID",
            err=True,
        )
        raise typer.Exit(code=2)

    cover_bytes, cover_note = _resolve_cover(cover)
    ctx.cover_image = cover_bytes

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
    structure_path = _write_structure_md(
        out, doc, ctx.structure_map, include_appendices=config.profile.include_appendices
    )
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
    typer.echo(f"  structure map     : {structure_path}  (Gate A artifact)")
    typer.echo(f"  chunk plan        : {chunks_path}")
    typer.echo(f"  {audio_label:<18}: {audio_list} ({total_bytes} bytes)")
    typer.echo(f"  cover             : {cover_note}")
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


def _run_extraction_qc(markdown: str, ctx: Context) -> ExtractionQCReport:
    """One cached LLM audit of the markdown. Keyed by version + backend + markdown digest, so
    a re-run is free and a mock (empty) result is never cached over a real one."""
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    payload = f"{EXTRACTION_QC_VERSION}\n{type(ctx.llm).__name__}\n{digest}"
    key = "extqc." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    cached = ctx.cache.get(key)
    if cached is not None:
        return parse_qc(cached.decode("utf-8"))
    report = parse_qc(
        ctx.llm.complete(
            build_qc_prompt(markdown),
            system=EXTRACTION_QC_SYSTEM,
            max_tokens=EXTRACTION_QC_MAX_TOKENS,
        )
    )
    if not report.is_empty():
        ctx.cache.put(key, report.model_dump_json().encode("utf-8"))
    return report


@app.command(name="check-extraction")
def check_extraction(
    markdown: Annotated[Path, typer.Argument(help="Markdown file from a standalone Marker run.")],
    llm: Annotated[
        str, typer.Option("--llm", help="mock (offline, no audit) or anthropic (real Opus audit).")
    ] = "anthropic",
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("out"),
    cache_dir: Annotated[Path, typer.Option(help="Cache directory.")] = Path(".cache/tts"),
) -> None:
    """LLM oversight of the extraction: audit a Marker markdown for extraction defects.

    Opus reads the markdown and flags OCR garble, broken/dropped equations, merged or
    truncated blocks, missing/misordered sections, and mangled tables/figures - BEFORE the
    document goes downstream. It only reports (with verbatim anchors); it never rewrites the
    text. Writes out/<name>.extraction-qc.md. One cached call, so a re-run is free.
    """
    if not markdown.exists():
        typer.echo(f"error: markdown file not found: {markdown}", err=True)
        raise typer.Exit(code=2)
    use_real_llm = _validate_llm(llm)
    if use_real_llm and not os.environ.get("ANTHROPIC_API_KEY"):
        typer.echo("error: --llm anthropic needs ANTHROPIC_API_KEY set in this shell.", err=True)
        raise typer.Exit(code=2)

    config = Config(cache_dir=str(cache_dir))
    ctx = build_context(config, pdf_bytes=b"", log_enabled=False, use_real_llm=use_real_llm)
    report = _run_extraction_qc(markdown.read_text(encoding="utf-8"), ctx)

    out.mkdir(parents=True, exist_ok=True)
    report_path = out / f"{markdown.stem}.extraction-qc.md"
    report_path.write_text(render_qc_md(report), encoding="utf-8")

    high = sum(1 for i in report.issues if i.severity == "high")
    typer.echo("Extraction QC  (LLM oversight of the Marker extraction)")
    typer.echo(f"  markdown : {markdown}")
    typer.echo(f"  backend  : {'anthropic (real)' if use_real_llm else 'mock'}")
    typer.echo(f"  issues   : {len(report.issues)} ({high} high severity)")
    typer.echo(f"  report   : {report_path}")
    if not use_real_llm:
        typer.echo("  (mock LLM did no real audit; pass --llm anthropic for the Opus review)")


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
