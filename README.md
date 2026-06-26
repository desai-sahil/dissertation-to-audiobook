# Thesis-to-Audiobook

Convert a PhD thesis PDF into a navigable audiobook through a typed, testable pipeline:

```
PDF -> structured IR -> reviewable spoken script (Gate B) -> cached TTS -> M4B
```

Status: **M0–M2 complete** (skeleton, deterministic normalization core, real parsing +
IR cleanup). LLM equation/table glosses (M3) and ElevenLabs TTS + M4B assembly (M4) are
not built yet, so TTS output is a deterministic silent placeholder for now.

## Prerequisites

- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)** (`pip install uv`)
- **poppler** for the offline parser — macOS: `brew install poppler` (provides `pdftotext`)

Optional, only for the production parsing path (otherwise use `--parser poppler`):

- **Docker** to run **GROBID** (citation linkage): `docker run --rm -p 8070:8070 grobid/grobid:0.8.0`
- **Marker** (primary PDF parser): `uv pip install marker-pdf` (downloads several GB of ML models)
- **ffmpeg** is only needed later, for M4 audio assembly.

## Setup

```bash
git clone <repo> && cd cornell-thesis-to-audiobook   # or just cd into it
uv sync                                               # creates .venv, installs deps
```

## Run it (offline — works out of the box)

Parse your PDF to the cleaned IR and see structure, citation linkage, and Gate A warnings:

```bash
uv run audiobook parse sample/Chapter6_preview.pdf --parser poppler -o out/sample.ir.json
open out/sample.ir.json          # the parsed IR
```

Run the whole pipeline (parse -> select -> normalize -> script -> chunk plan):

```bash
uv run audiobook run sample/Chapter6_preview.pdf --dry-run --parser poppler
open out/conclusions-and-future-work.script.md   # the Gate B reviewable script
```

`--profile committee` (default) keeps citations; `--profile general` drops them.
Swap in your own thesis by pointing at any PDF path.

## Test it

```bash
uv run pytest                       # full offline suite (currently 189 passed, 2 deselected)
uv run pytest --cov=thesis_audiobook --cov-report=term-missing
uv run pyright                      # strict type check (src) -> 0 errors
uv run ruff check . && uv run ruff format --check .
```

The suite is fully offline: parser contract tests replay committed cassettes under
`tests/fixtures/cassettes/`, and an autouse cost guard makes any real ElevenLabs/LLM
call fail. Tests that need real tools or services are marked `live` and skipped by
default.

## Production parsing path (Marker + GROBID)

```bash
# 1. start GROBID (separate terminal)
docker run --rm -p 8070:8070 grobid/grobid:0.8.0
# 2. install Marker
uv pip install marker-pdf
# 3. parse with the real tools (better math/structure fidelity than poppler)
uv run audiobook parse sample/Chapter6_preview.pdf --parser marker -o out/marker.ir.json
# 4. run the live integration test
uv run pytest -m live
```

Marker/MinerU are local and free; only ElevenLabs (TTS) and the LLM cost money, and
neither is invoked yet. See [CLAUDE.md](CLAUDE.md) and [specs/](specs/) for architecture
and milestones.
