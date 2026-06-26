# Thesis-to-Audiobook

Convert a PhD thesis PDF into a navigable audiobook through a typed, testable pipeline:

```
PDF -> structured IR -> LLM pronunciation curation -> reviewable spoken script (Gate B)
    -> cached TTS -> M4B / MP4 / per-chapter MP3 (with chapter markers + provenance)
```

Every transform is pure and deterministic; all I/O (PDF parsing, LLM, TTS, ffmpeg,
cache) lives in adapters behind ports. The same PDF and config produce the same script
byte-for-byte, and rendered audio is content-addressed cached, so re-renders are free.

Status: **M0–M5 complete.** Deterministic normalization core, real parsing (Marker/MinerU
+ GROBID, or an offline poppler fallback), LLM equation/table glosses, ElevenLabs TTS +
ffmpeg assembly, an LLM pronunciation curator, and TOML-driven profiles. Offline runs use
deterministic mocks (silent audio, no model calls); real audio needs the keys below.

## Prerequisites

- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)** (`pip install uv`)
- **poppler** for the offline parser — `brew install poppler` (provides `pdftotext`)

For real audio (otherwise everything runs offline on mocks):

- **ffmpeg** — `brew install ffmpeg` (no admin? use micromamba/conda-forge or a static build)
- **`ELEVENLABS_API_KEY`** + a real voice id, and **`ANTHROPIC_API_KEY`** (glosses + curator)

For the highest-fidelity parser (optional; removes poppler's notation/citation artifacts):

- **Docker** for **GROBID**: `docker run --rm -p 8070:8070 grobid/grobid:0.8.0`
- **Marker**: `uv pip install marker-pdf`, then `--parser marker`

## Setup

```bash
uv sync          # creates .venv, installs deps
```

## Run it offline (works out of the box, free)

```bash
# cost estimate + chunk plan, zero external calls:
uv run audiobook run sample/Chapter6_preview.pdf --dry-run --parser poppler

# full pipeline on mocks -> stand-in audio + the Gate B script:
uv run audiobook run sample/Chapter6_preview.pdf --parser poppler --tts mock
open out/conclusions-and-future-work.script.md     # the reviewable spoken script
```

## Render real audio

```bash
export ANTHROPIC_API_KEY=...        # equation glosses + the pronunciation curator
export ELEVENLABS_API_KEY=...
export ELEVENLABS_VOICE_ID=...      # a real voice id (or pass --voice)

uv run audiobook run sample/Chapter6_preview.pdf \
  --parser poppler --llm anthropic --tts elevenlabs --format mp4 --cover cover/cover01.png
open out/conclusions-and-future-work.mp4
```

Outputs land in `out/`: the chaptered audio (`.m4b` or `.mp4`) **plus** a single
whole-book `.mp3` alongside it (`--format mp3` emits only that one file), the Gate B
`.script.md`, the `.chunks.json` plan, a `.provenance.json` sidecar (audio timestamp ->
source block id), and `.qa.md` (what the curator decided + anything it flagged). If a
cover image is given, the `.mp4` shows it for the whole runtime and the `.m4b`/`.mp3`
embed it as album art; with no cover the renders are audio-only.

### `run` options

| Flag | Meaning |
|---|---|
| `--parser poppler\|marker\|mineru` | PDF parser (poppler is offline; marker is highest fidelity) |
| `--llm mock\|anthropic` | equation glosses + pronunciation curator (anthropic costs money) |
| `--tts mock\|elevenlabs` | speech synthesis (elevenlabs costs money; needs ffmpeg) |
| `--format m4b\|mp4\|mp3` | chaptered file (m4b/mp4) + a whole-book mp3; `mp3` emits only the mp3 |
| `--cover <path>` | cover image (default `cover/cover01.png`); mp4 shows it, m4b/mp3 embed it; omit to skip |
| `--voice <id>` | ElevenLabs voice id (or set `ELEVENLABS_VOICE_ID`) |
| `--profile committee\|general` | listener profile (see below) |
| `--preview` | render the first chapter only, with the cheap flash model |
| `--no-curate` | skip the LLM pronunciation curator |
| `--dry-run` | cost estimate + chunk plan, zero external calls |
| `--cache-dir <path>` | content-addressed TTS/plan cache (default `.cache/tts`) |

## Profiles

Profiles are validated TOML data files in
[src/thesis_audiobook/data/profiles/](src/thesis_audiobook/data/profiles/) — edit them to
retune without touching code. `committee` (default) glosses equations, summarizes tables,
and speaks brief citations; `general` announces equations, skips tables, and drops citations.

## The pronunciation curator

With `--llm anthropic`, an LLM reads the whole document once and returns a structured
plan: acronyms (expand on first use, then a short form), domain term pronunciations, and
flattened-notation reads. It changes only *how* terms are said, never the prose. The plan
is content-addressed cached (one model call per document; re-renders reuse it) and written
to `out/<slug>.qa.md` for review. Offline (`--llm mock`) it is a no-op.

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

See [CLAUDE.md](CLAUDE.md) and [specs/](specs/) for the architecture and milestones.
