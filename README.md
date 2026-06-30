<div align="center">

<a href="https://desai-sahil.github.io/dissertation-to-audiobook/">
  <img src="cover/cover01-web.jpg" width="380" alt="Dissertation-to-Audiobook cover">
</a>

# Dissertation-to-Audiobook

### [https://desai-sahil.github.io/dissertation-to-audiobook/](https://desai-sahil.github.io/dissertation-to-audiobook/)

</div>

Turn a PhD thesis PDF into a navigable, faithful audiobook: M4B / MP4 / MP3 with chapter
markers and a cover.

Faithful by construction: every value, sign, and claim is preserved. Equations are announced by
number; figure/table captions, citation markers, and the bibliography are dropped; front matter is
read and back matter is skipped.

## Setup

```bash
uv sync                       # the pipeline (Python 3.12+)
brew install poppler ffmpeg   # PDF text extraction + audio assembly
```

Set three keys for a real audiobook:

```bash
export ANTHROPIC_API_KEY=...    # the LLM passes: structure, pronunciation, QC
export ELEVENLABS_API_KEY=...   # the narration voice
export ELEVENLABS_VOICE_ID=...  # which voice
```

Without keys, everything still runs offline on free mocks (silent audio).

## Try it (offline, no keys)

```bash
uv run audiobook run tests/fixtures/Chapter6_preview.pdf --parser poppler --tts mock
```

Writes a reviewable script + stand-in audio to `out/`, with zero external calls.

## Make your audiobook

Drop your thesis PDF into `sample/` and put your cover at `cover/cover01.png` (or use `--cover`).

**1. Prepare the script and check the cost** (runs the LLM passes; no audio spend yet):

```bash
uv run audiobook run sample/your-thesis.pdf --parser poppler --llm anthropic --tts mock
```

Review the script written to `out/` and the printed `est. TTS cost`.

**2. Render the audiobook** (reuses the script from step 1; bills ElevenLabs):

```bash
uv run audiobook run sample/your-thesis.pdf \
  --parser poppler --llm anthropic --tts elevenlabs --format mp4
```

Outputs land in `out/`: the chaptered `.mp4`/`.m4b`, a whole-book `.mp3`, the cover, and the script.

> For the highest fidelity on a dense thesis (vision-grounded narration + a cover generated from
> your title and author), use the `run-v2` engine. See [specs/](specs/).

## Develop

```bash
uv run pytest        # offline test suite
uv run ruff check .  # lint
uv run pyright       # strict types
```

Architecture and conventions live in [CLAUDE.md](CLAUDE.md) and [specs/](specs/).
