<div align="center">

<a href="https://desai-sahil.github.io/dissertation-to-audiobook/">
  <img src="cover/cover01-web.jpg" width="380" alt="Dissertation-to-Audiobook cover">
</a>

# Dissertation-to-Audiobook

### [https://desai-sahil.github.io/dissertation-to-audiobook/](https://desai-sahil.github.io/dissertation-to-audiobook/)

</div>

Turn a PhD thesis PDF into a navigable, faithful audiobook: M4B / MP4 / MP3 with chapter
markers and an auto-generated cover.

The model writes the spoken text and a **deterministic verifier** is the faithfulness floor
(every value, sign, and claim preserved and in order; no invented numbers), with the hard parts
grounded in the page image. Equations are announced by number; figure/table captions, citation
markers, and the bibliography are dropped; front matter is read and back matter is skipped.

## Setup

```bash
uv sync   # Python 3.12+
```

Offline runs are free (deterministic mocks, silent audio). Real audio needs **poppler** and
**ffmpeg** (`brew install poppler ffmpeg`), plus `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY`
with a voice id.

## Quickstart (offline, no keys)

```bash
uv run audiobook run tests/fixtures/Chapter6_preview.pdf --parser poppler --tts mock
```

Produces the reviewable script and stand-in audio in `out/`, with no external calls.

## Make the audiobook

Convert the thesis PDF to markdown with **Marker** first (`uv tool install marker-pdf`, run it
standalone since its dependencies conflict with this project's), then:

```bash
export ANTHROPIC_API_KEY=...  ELEVENLABS_API_KEY=...  ELEVENLABS_VOICE_ID=...
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/your-thesis.cleaned.md \
  --llm anthropic --tts elevenlabs --format mp4
```

- `--preview` renders only the first chapter (a cheap end-to-end test).
- `--cover <path>` overrides the cover that is otherwise generated from the title and author.
- Drop `--tts elevenlabs` for a free mock render; it prints the real TTS cost first.

Outputs land in `out/`: the chaptered `.mp4`/`.m4b`, a whole-book `.mp3`, the cover, the
reviewable script, and a provenance sidecar.

## Develop

```bash
uv run pytest        # offline test suite
uv run ruff check .  # lint
uv run pyright       # strict types
```

Architecture and conventions live in [CLAUDE.md](CLAUDE.md) and [specs/](specs/).
