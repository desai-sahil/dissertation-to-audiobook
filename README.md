<div align="center">

<a href="https://desai-sahil.github.io/dissertation-to-audiobook/">
  <img src="cover/cover01-web.jpg" width="380" alt="Dissertation-to-Audiobook cover">
</a>

# Dissertation-to-Audiobook

### [https://desai-sahil.github.io/dissertation-to-audiobook/](https://desai-sahil.github.io/dissertation-to-audiobook/)

</div>

Turn a PhD thesis PDF into a navigable, faithful audiobook: M4B / MP4 / MP3 with chapter
markers and a cover.

The model writes the spoken text and a **deterministic verifier** is the faithfulness floor
(every value, sign, and claim preserved and in order; no invented numbers), with the hard parts
grounded in the page image. Equations are announced by number; figure/table captions, citation
markers, and the bibliography are dropped; front matter is read and back matter is skipped.

## Setup

```bash
uv sync                       # the pipeline (Python 3.12+)
brew install poppler ffmpeg   # PDF text extraction + audio assembly
uv tool install marker-pdf    # PDF -> markdown (separate tool; its deps conflict with ours)
```

For real audio, set `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, and `ELEVENLABS_VOICE_ID`.
Everything also runs offline on free mocks (silent audio, no keys).

## Confirm the install (offline, no keys)

```bash
uv run audiobook run tests/fixtures/Chapter6_preview.pdf --parser poppler --tts mock
```

Writes a reviewable script + stand-in audio to `out/`, with zero external calls.

## Make an audiobook

Drop your thesis PDF into `sample/`, then:

**1. PDF → markdown** with Marker:

```bash
marker_single sample/your-thesis.pdf --output_dir out/marker
# writes out/marker/your-thesis/your-thesis.md
```

**2. Render** the audiobook:

```bash
export ANTHROPIC_API_KEY=...  ELEVENLABS_API_KEY=...  ELEVENLABS_VOICE_ID=...
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/marker/your-thesis/your-thesis.md \
  --llm anthropic --tts elevenlabs --format mp4
```

Run it once **without** `--tts elevenlabs` first: a free dry run that writes the script and
cover and prints the ElevenLabs cost before you spend.

**Cover:** auto-generated from the title and author by default; add `--cover cover/cover01.png`
(any PNG or JPEG) to use your own.
**Other flags:** `--preview` (first chapter only), `--format m4b|mp4|mp3`.

Outputs land in `out/`: the chaptered `.mp4`/`.m4b`, a whole-book `.mp3`, the cover, the
reviewable script, and a provenance sidecar.

## Develop

```bash
uv run pytest        # offline test suite
uv run ruff check .  # lint
uv run pyright       # strict types
```

Architecture and conventions live in [CLAUDE.md](CLAUDE.md) and [specs/](specs/).
