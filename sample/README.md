# sample/

Drop a thesis PDF here, then run it through the pipeline:

```bash
# v2 engine (recommended): needs a Marker-produced markdown as the narration source
audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/your-thesis.cleaned.md \
  --llm anthropic --tts elevenlabs --format mp4
```

This folder ships **empty** — no thesis PDFs are committed. (The test suite's tiny
fixture lives in `tests/fixtures/Chapter6_preview.pdf`, not here.)

**Uploading a big thesis to GitHub:** GitHub rejects any single file larger than
**100 MB** on push, and a full thesis PDF often exceeds that. Two options:

- Track it with **Git LFS** before committing: `git lfs track "sample/*.pdf"`
  (this writes a `.gitattributes` entry; you also need `git lfs install` once).
- Or keep it local only: add `sample/*.pdf` to `.gitignore`.
