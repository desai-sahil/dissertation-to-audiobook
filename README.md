# Thesis-to-Audiobook

Convert a PhD thesis PDF into a navigable audiobook through a typed, testable pipeline:

```
PDF --(Marker)--> markdown --(QC: audit + guarded repair)--> clean markdown
    --> structured IR --> LLM structure map (what to read vs skip)
    --> reviewable spoken script --(pre-TTS QC gate)--> cached TTS
    --> M4B / MP4 / per-chapter MP3 (chapter markers + provenance)
```

Every transform is pure and deterministic; all I/O (PDF parsing, LLM, TTS, ffmpeg, cache)
lives in adapters behind ports. The same input and config produce the same script
byte-for-byte, and rendered audio is content-addressed cached, so re-renders are free. The
LLM never writes spoken prose from scratch: it only labels structure and pronunciation, and
rendering is deterministic, so it cannot hallucinate narration.

Status: the deterministic normalization core, real parsing (Marker/MinerU markdown, or an
offline poppler fallback), an LLM **cartographer** that maps document structure, a
pronunciation **curator**, a two-pass **extraction QC**, a **pre-TTS script QC gate**,
ElevenLabs TTS + ffmpeg assembly, and TOML-driven profiles are all in place and validated
end to end on a full 360-page thesis. Offline runs use deterministic mocks (silent audio,
no model calls); real audio needs the keys below.

## What is read, and what is skipped

- **Equations** are announced by their real number ("Equation two point three"), not read
  symbol by symbol and not glossed by an LLM. Unnumbered intermediate steps are dropped.
- **Figure and table captions** are skipped (heavily visual: "Panel A", colors).
- **Bibliographies / reference lists** are skipped; in-text citations read as author-year
  ("Buckley and Mott twenty thirteen"), or author-only when no year is available.
- **Front matter** (abstract, biographical sketch, acknowledgements, dedication) is read;
  the table of contents, list of figures/tables, and appendices are skipped.

## Prerequisites

- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)** (`pip install uv`)
- **poppler** for the offline parser — `brew install poppler` (provides `pdftotext`)

For real audio (otherwise everything runs offline on mocks):

- **ffmpeg** — `brew install ffmpeg` (no admin? use micromamba/conda-forge or a static build)
- **`ELEVENLABS_API_KEY`** + a real voice id, and **`ANTHROPIC_API_KEY`** (cartographer,
  curator, table summaries, and the two QC passes)

For the highest-fidelity ingestion of a complex thesis (recommended for the real deliverable):

- **Marker** as an isolated tool: `uv tool install marker-pdf`, then run it standalone and
  feed the markdown with `--markdown` (see Phase 1). Marker is kept out of this project's
  environment on purpose (its pins conflict with ours).

## Setup

```bash
uv sync          # creates .venv, installs deps
```

## Quickstart (offline, free, works out of the box)

```bash
# cost estimate + chunk plan, zero external calls:
uv run audiobook run sample/Chapter6_preview.pdf --dry-run --parser poppler

# full pipeline on mocks -> stand-in audio + the reviewable script:
uv run audiobook run sample/Chapter6_preview.pdf --parser poppler --tts mock
open out/conclusions-and-future-work.script.md
```

## The five-phase workflow (full thesis -> real audiobook)

A complex thesis goes through five explicit phases. Phases 1–2 prepare a clean markdown
once; phase 3 onward is the repeatable `run`. The phase banners print as `run` executes.

### Phase 1 — Ingest with Marker

Marker (run standalone, outside this repo's venv) converts the PDF to markdown:

```bash
marker_single sample/Jain_cornellgrad_0058F_13867.pdf --output_dir out/marker
# -> out/Jain_cornellgrad_0058F_13867.md
```

### Phase 2 — Extraction QC (audit, then guarded repair)

Opus audits the markdown for extraction defects, then repairs them under a safety guard
(the LLM proposes; code applies only edits that preserve the token sequence; the LLM
re-checks). Output is one coherent `*.cleaned.md`.

```bash
uv run audiobook check-extraction  out/Jain_cornellgrad_0058F_13867.md --llm anthropic
uv run audiobook repair-extraction out/Jain_cornellgrad_0058F_13867.md --llm anthropic
# -> out/Jain_cornellgrad_0058F_13867.cleaned.md  (+ a QC report)
```

### Phase 3 — Prepare the narration script

`run` ingests the clean markdown and builds the reviewable script:
build IR → **cartographer** (LLM structure map: chapters vs front/back matter) → select →
math (announce equations) → figures (skip captions) → citations (author-year) → normalize →
assemble. Artifacts are written **before** any TTS spend.

```bash
uv run audiobook run sample/Jain_cornellgrad_0058F_13867.pdf \
  --markdown out/Jain_cornellgrad_0058F_13867.cleaned.md \
  --llm anthropic --tts mock --format mp4
open out/<slug>.script.md          # the reviewable spoken script
open out/<slug>.structure.md       # the cartographer's keep/skip decisions
```

Before the artifacts are written, a **guarded auto-repair loop** runs (a generator-verifier
loop). Each round: a *writer* (Opus) proposes small find/replace pronunciation fixes; each
must clear **two independent safety layers** before it is applied —

1. a **deterministic no-fabrication guard** (the replacement may add no number, year, or
   name absent from the text it replaces), and
2. an independent **auditor panel** — two adversarial Opus calls, each grounded only on the
   original span and the proposed output, both must vote *faithful* (fail-closed). The panel
   catches what the guard cannot: a flipped claim or relation ("increased" → "decreased")
   that adds no new number or name.

Survivors are applied, the script is re-read, and the loop repeats until a round verifies
nothing (convergence). So the writer gets broad latitude to *change how text sounds* and
zero latitude to *invent facts*. Every call is cached (deterministic, cheap to re-run); the
applied/rejected list lands at `out/<slug>.script-repair.md`. Disable with `--no-script-repair`.
The auditor is red-teamed against planted fabrications in the `live` test suite.

### Phase 4 — Pre-TTS script QC gate

Opus audits the (post-repair) script for red flags that would sound wrong (leaked markup,
truncated sentences, OCR garble, mispronunciations). The report lands at
`out/<slug>.script-qc.md`. The audit is read-only by design; the guarded repair above
auto-applies the safe fixes, and the remaining class-level ones become deterministic
transforms. With `--tts elevenlabs`, **high-severity flags block the render** so you never
pay to synthesize broken audio (override with `--force`).

### Phase 5 — Render + assemble

ElevenLabs renders the (content-addressed cached) chunks; ffmpeg muxes the chaptered file.

```bash
export ANTHROPIC_API_KEY=...
export ELEVENLABS_API_KEY=...
export ELEVENLABS_VOICE_ID=...     # a real voice id (or pass --voice)

uv run audiobook run sample/Jain_cornellgrad_0058F_13867.pdf \
  --markdown out/Jain_cornellgrad_0058F_13867.cleaned.md \
  --llm anthropic --tts elevenlabs --cover cover/cover01.png --format mp4
```

Outputs land in `out/`: the chaptered audio (`.m4b` or `.mp4`) **plus** a whole-book `.mp3`
(`--format mp3` emits only that), the `.script.md`, the `.structure.md`, the
`.script-qc.md`, the `.chunks.json` plan, a `.provenance.json` sidecar (audio timestamp ->
source block id), and `.qa.md` (the curator's decisions). A cover image shows for the whole
runtime in the `.mp4` and embeds as album art in the `.m4b`/`.mp3`; omit it for audio-only.

## `run` options

| Flag | Meaning |
|---|---|
| `--markdown <path>` | ingest a pre-parsed Marker/MinerU markdown file (sets `--parser markdown`) |
| `--parser poppler\|marker\|mineru\|markdown` | PDF parser; poppler is offline, markdown ingests phase-1 output |
| `--llm mock\|anthropic` | cartographer + curator + table summaries + QC (anthropic costs money) |
| `--tts mock\|elevenlabs` | speech synthesis (elevenlabs costs money; needs ffmpeg) |
| `--format m4b\|mp4\|mp3` | chaptered file (m4b/mp4) + a whole-book mp3; `mp3` emits only the mp3 |
| `--cover <path>` | cover image (default `cover/cover01.png`); omit to render audio-only |
| `--voice <id>` | ElevenLabs voice id (or set `ELEVENLABS_VOICE_ID`) |
| `--profile committee\|general` | listener profile (see below) |
| `--preview` | render the first chapter only, with the cheap flash model |
| `--no-structure-eval` | skip the cartographer (use deterministic structure detection) |
| `--no-curate` | skip the LLM pronunciation curator |
| `--no-script-repair` | skip the guarded auto-repair (safe pronunciation fixes) |
| `--no-script-qc` | skip the phase-4 pre-TTS script QC check |
| `--force` | render even if phase-4 QC finds high-severity red flags |
| `--dry-run` | cost estimate + chunk plan, zero external calls |
| `--cache-dir <path>` | content-addressed TTS/plan cache (default `.cache/tts`) |

Because the cartographer, curator, and QC outputs are content-addressed cached, re-running
phase 3+4 on unchanged markdown reuses them with **no LLM billing** — only the deterministic
transforms re-run. That is the loop: QC flags a defect, a deterministic transform is fixed,
you re-run cheaply, the gate clears.

## Profiles

Profiles are validated TOML data files in
[src/thesis_audiobook/data/profiles/](src/thesis_audiobook/data/profiles/) — edit them to
retune without touching code. Both profiles announce equations by number; they differ on
tables and citations: `committee` (default) summarizes tables (LLM) and speaks brief
citations; `general` skips tables and drops citations.

## The cartographer and curator

- **Cartographer** (`--llm anthropic`): reads the document once and returns a structure map
  — which regions are chapters/body (read) versus table of contents, lists, bibliographies,
  and appendices (skipped). It returns only region labels and existing block boundaries;
  the keep/skip rendering is deterministic. Written to `out/<slug>.structure.md`.
- **Curator** (`--llm anthropic`): returns a pronunciation plan — acronyms (expand on first
  use, then a spelled short form), domain terms, and flattened-notation reads. It changes
  only *how* terms are said, never the prose. Single-letter and bare Greek-letter keys are
  ignored (they collide with initials, the article "A", and overloaded symbols). Written to
  `out/<slug>.qa.md`.

Both are cached one call per document and are no-ops offline (`--llm mock`).

## Test it

```bash
uv run pytest                                        # full offline suite
uv run pyright                                       # strict types (src) -> 0 errors
uv run ruff check . && uv run ruff format --check .
uv run pytest -m live                                # opt-in tests that hit real services
```

The suite is fully offline: parser contract tests replay committed cassettes, the LLM/TTS
are mocked, and an autouse cost guard makes any real ElevenLabs/Anthropic call fail. Tests
needing real tools/keys are marked `live` and skipped by default.

See [CLAUDE.md](CLAUDE.md) and [specs/](specs/) for the architecture and conventions.
