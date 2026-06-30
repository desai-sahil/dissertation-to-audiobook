<div align="center">

<a href="https://desai-sahil.github.io/dissertation-to-audiobook/">
  <img src="cover/cover01-web.jpg" width="380" alt="Dissertation-to-Audiobook cover">
</a>

# Dissertation-to-Audiobook

### [https://desai-sahil.github.io/dissertation-to-audiobook/](https://desai-sahil.github.io/dissertation-to-audiobook/)

</div>

Turn a PhD thesis PDF into a navigable, faithful audiobook: M4B / MP4 / MP3 with chapter
markers and a cover.

The model narrates each section and a deterministic verifier guarantees faithfulness, grounded in
the page image so it holds up on dense, notation-heavy theses: every value, sign, and claim is
preserved. Equations are announced by number; figure/table captions, citation markers, and the
bibliography are dropped; front matter is read and back matter is skipped.

## Setup

```bash
uv sync                       # the pipeline (Python 3.12+)
brew install poppler ffmpeg   # PDF rendering + audio assembly
uv tool install marker-pdf    # PDF -> markdown (separate tool; its deps conflict with the pipeline's)
```

Set three keys:

```bash
export ANTHROPIC_API_KEY=...    # narration + structure
export ELEVENLABS_API_KEY=...   # the voice
export ELEVENLABS_VOICE_ID=...  # which voice
```

## Make your audiobook

Drop your thesis PDF into `sample/`, then:

**1. Convert the PDF to markdown** (once):

```bash
marker_single sample/your-thesis.pdf --output_dir out/marker
# writes out/marker/your-thesis/your-thesis.md
```

**2. Prepare the script and check the cost** (no audio spend yet):

```bash
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/marker/your-thesis/your-thesis.md \
  --llm anthropic --format mp4
```

Review the script written to `out/` and the printed TTS cost.

**3. Render the audiobook** (reuses step 2; bills ElevenLabs):

```bash
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/marker/your-thesis/your-thesis.md \
  --llm anthropic --tts elevenlabs --format mp4
```

**Choose your cover.** A cover is generated from your thesis title and author by default. To use your
own instead, add `--cover path/to/your-cover.png` (PNG or JPEG); a square image works best (it shows
for the whole runtime in the `.mp4` and as album art in the `.m4b`/`.mp3`):

```bash
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/marker/your-thesis/your-thesis.md \
  --llm anthropic --tts elevenlabs --format mp4 \
  --cover path/to/your-cover.png
```

Outputs land in `out/`: the chaptered `.mp4`/`.m4b`, a whole-book `.mp3`, the cover, the script,
and a provenance sidecar.

## Develop

```bash
uv run pytest        # offline test suite
uv run ruff check .  # lint
uv run pyright       # strict types
```

Architecture and conventions live in [CLAUDE.md](CLAUDE.md) and [specs/](specs/).
