<div align="center">

<a href="https://desai-sahil.github.io/dissertation-to-audiobook/">
  <img src="cover/cover01-web.jpg" width="380" alt="Dissertation-to-Audiobook cover">
</a>

# Dissertation-to-Audiobook

## [View the project site →](https://desai-sahil.github.io/dissertation-to-audiobook/)

</div>

Convert a PhD thesis PDF into a navigable audiobook through a typed, testable pipeline:

```
PDF --(Marker)--> markdown --(QC: audit + guarded repair)--> clean markdown
    --> structured IR --> LLM structure map (what to read vs skip)
    --> reviewable spoken script --(pre-TTS QC gate)--> cached TTS
    --> M4B / MP4 / per-chapter MP3 (chapter markers + provenance)
```

Every transform is pure and deterministic; all I/O (PDF parsing, LLM, TTS, ffmpeg, cache)
lives in adapters behind ports. The same input and config produce the same script
byte-for-byte, and rendered audio is content-addressed cached, so re-renders are free.

**Two engines.** The original **v1** (`run`) is claim-safe *by construction*: the LLM only
labels structure and pronunciation, deterministic code renders the spoken text, so it cannot
hallucinate narration. The current **v2** (`run-v2`, recommended) inverts that split to
generalize across theses: the LLM writes the faithful spoken text and a **deterministic
verifier** is the floor (every value preserved and in order, no invented number or claim,
polarity/direction intact, near-paraphrase not free composition), with the hard parts
grounded in the **page image**. See [The v2 engine](#the-v2-engine-run-v2-recommended) below.

Status: both engines run end to end and are validated on real theses (Gao, Zhu, Jain;
faithfulness ~0.96-0.995). Offline runs use deterministic mocks (silent audio, no model
calls); real audio needs the keys below.

## What is read, and what is skipped

- **Equations** are announced by their real number ("Equation two point three"), not read
  symbol by symbol and not glossed by an LLM. Unnumbered intermediate steps are dropped.
- **Figure and table captions** are skipped (heavily visual: "Panel A", colors).
- **Citations are treated as machinery, not narration** (NotebookLM-style): reference markers
  ("[12]", superscript numbers, "(Geiger et al., 2009)") are stripped, and narrative author
  mentions are genericized ("Chalmer et al. note that…" → "researchers note that…"). The
  bibliography is not parsed or read.
- **Front matter** (abstract, biographical sketch, acknowledgements, dedication) is read;
  the table of contents, list of figures/tables, and appendices are skipped.

## The v2 engine (`run-v2`, recommended)

v2 is vision-grounded and generalizes across theses without a per-thesis surface-form
treadmill. Instead of deterministic code rendering spoken text from LLM labels (v1), the
**LLM writes the spoken text** and a **deterministic verifier** is the faithfulness floor.

```
PDF --> page images (ground truth) + per-page text (alignment aid)
    --> vision cartographer (read vs skip section kinds)
    --> verifier-gated narrator (re-narrate, then escalate to the page image, else hold)
    --> announce equations / skip non-prose --> assemble
    --> cached TTS --> M4B / MP4 / MP3 + generated cover + provenance
```

- **Vision cartographer** reads the page images and labels each top-level section's *kind*
  (body chapter, abstract, acknowledgements, references, appendix, ...), so structure is
  recognized semantically rather than by heading regex. Read/skip policy is the same as above.
- **Verifier-gated narrator.** For each read segment the model writes the spoken text; the
  deterministic verifier (`verifier.py`) checks invariants — values preserved and in order, no
  invented number/claim, negation/scope/direction intact, near-paraphrase not free
  composition, a speakable-character allowlist. On a failure it re-narrates, then **escalates
  to the page image** (the page is ground truth) before holding the segment for review.
- **Generated cover.** Unless you pass `--cover`, v2 renders the title + author onto
  `cover/cover - generic.png` (Newsreader title, Space Mono labels) → `out/<slug>.cover.png`.
- **Cost safety.** `--tts mock` is the free default; a high held/flagged rate prints
  NEEDS REVIEW and stops before a billed ElevenLabs render unless `--force`. The TTS cache key
  includes the backend, so a mock render's silent audio is never served to a real one.

```bash
# free end-to-end dry check (mock TTS): script + cover + cost estimate, no billing
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/your-thesis.cleaned.md \
  --llm anthropic --format mp4 --preview

# the real render (billed ElevenLabs), MP4 + MP3 with the generated cover
export ANTHROPIC_API_KEY=...  ELEVENLABS_API_KEY=...  ELEVENLABS_VOICE_ID=...
uv run audiobook run-v2 sample/your-thesis.pdf \
  --markdown out/your-thesis.cleaned.md \
  --llm anthropic --tts elevenlabs --format mp4 --preview   # drop --preview for the whole book
```

Outputs land in `out/` (and `out/preview/` for `--preview`): the chaptered `.mp4`/`.m4b` +
whole-book `.mp3` (cover shown/embedded), `.cover.png`, `.script.md`, `.v2-pairs.json`
(source/spoken faithfulness pairs), and `.provenance.json`.

| `run-v2` flag | Meaning |
|---|---|
| `--markdown <path>` | the narration source markdown (required) |
| `--llm mock\|anthropic` | vision + narration (anthropic costs money; bounded calls, all cached) |
| `--llm-model <id>` | model for vision + narration (default `claude-sonnet-4-6`) |
| `--dpi <n>` | page-render DPI for the vision read (default 100) |
| `--tts mock\|elevenlabs` | speech synthesis (elevenlabs costs money; needs ffmpeg) |
| `--format m4b\|mp4\|mp3` | chaptered file (m4b/mp4) + a whole-book mp3; `mp3` emits only the mp3 |
| `--cover <path>` | cover image; **omit to generate one** from the title + author |
| `--voice <id>` | ElevenLabs voice id (or set `ELEVENLABS_VOICE_ID`) |
| `--preview` | render only the first chapter + front matter (to `out/preview/`) |
| `--force` | render even if the confidence gate flags NEEDS REVIEW |
| `--profile committee\|general` | listener profile |

The rest of this README documents the **v1** `run` engine, whose deterministic core (parsing,
normalization, the QC loop, TTS/assembly) v2 reuses wholesale for everything after narration.

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
uv run audiobook run tests/fixtures/Chapter6_preview.pdf --dry-run --parser poppler

# full pipeline on mocks -> stand-in audio + the reviewable script:
uv run audiobook run tests/fixtures/Chapter6_preview.pdf --parser poppler --tts mock
open out/conclusions-and-future-work.script.md
```

## The five-phase workflow (full thesis -> real audiobook)

A complex thesis goes through five explicit phases. Phases 1–2 prepare a clean markdown
once; phase 3 onward is the repeatable `run`. The phase banners print as `run` executes.

### Phase 1 — Ingest with Marker

Marker (run standalone, outside this repo's venv) converts the PDF to markdown:

```bash
marker_single sample/your-thesis.pdf --output_dir out/marker
# -> out/your-thesis.md
```

### Phase 2 — Extraction QC (audit, then guarded repair)

The model audits the markdown for extraction defects, then repairs them under safety guards (the
LLM proposes, code applies only guard-passing edits, the LLM re-checks). Two edit kinds: **noise**
(typographic/OCR — must preserve the exact word-token sequence and case) and **artifact** —
de-shredding Marker-mangled notation (a decimal split into per-character `<sup>` tags like
`<sup>0</sup>.1` → `0.1`, a Miller index `< <sup>111</sup> >` → `1 1 1`), which must restore the
value using only the digits/symbols already present (ordered digits identical, no sign dropped or
invented) — so it re-renders faithfully but can never turn `0.15` into `0.5`. Output is one coherent
`*.cleaned.md` plus a `*.repair-report.md`.

```bash
uv run audiobook check-extraction  out/your-thesis.md --llm anthropic
uv run audiobook repair-extraction out/your-thesis.md --llm anthropic
# -> out/your-thesis.cleaned.md  (+ a QC report)
```

### Phase 3 — Prepare the narration script

`run` ingests the clean markdown and builds the reviewable script:
build IR → **structurer** (LLM block-kind classifier) → **cartographer** (LLM structure map:
chapters vs front/back matter) → select → math (announce equations) → figures (skip captions) →
citations (genericized) → normalize → assemble. Artifacts are written **before** any TTS spend.

The **structurer** is how block detection generalizes across theses without per-thesis regex:
Opus labels each block's *kind* (prose / heading / equation / code / figure / table / reference
/ frontmatter) and the deterministic layer renders or skips from the label — so a source-code
appendix (fenced or spaced-out) is typed `code` and skipped, whatever the formatting. Claim-safe
(it returns only a kind per block id, never text), and every type change is logged to
`out/<slug>.structure-changes.md`. Disable with `--no-structurer`.

```bash
uv run audiobook run sample/your-thesis.pdf \
  --markdown out/your-thesis.cleaned.md \
  --llm anthropic --tts mock --format mp4
open out/<slug>.script.md          # the reviewable spoken script
open out/<slug>.structure.md       # the cartographer's keep/skip decisions
```

Before the artifacts are written, an **auto-repair loop** runs. Each round a *writer* (LLM)
proposes small find/replace edits that fix how **notation is spoken** — units and symbols voiced
in full (`cm` → "centimeters"), leaked LaTeX/markup turned into words, chemical formulas read as
their name, number/ordinal spacing artifacts. The edits are applied as proposed and the loop
re-reads the script until a round changes nothing.

By default (**copy-edit mode**) it also fixes the author's clear **mechanical** errors so a
listener is not tripped up — spelling typos (`stomotal` → "stomatal"), fused words (`withincreasing`
→ "with increasing"), and meaning-preserving grammar (agreement, a missing article) — plus PDF
extraction artifacts. What it will **never** do is change the author's **data or claims**: numbers,
signs, units, and findings are protected, and anything that looks like a value/sign error is
**flagged for your review, never auto-changed**. Pass `--as-written` to turn copy-edit off and read
the thesis strictly verbatim (notation vocalization only).

The safety floor is a **deterministic guard**, not an LLM auditor: an author-text edit is applied
only if it preserves every value (digits *and* spelled-out numbers/units, Greek variable names),
every negation/scope word, and every directional result word ("increased", "higher", "positive"),
changing at most one content word in place. So a typo fix passes while `increased` → `decreased`,
`psi` → `phi`, `0.15` → `0.5`, or inserting "significant" is rejected. Edits also apply on **whole
tokens only**, so `mm` → "millimeters" can never rewrite inside a word ("co**mm**ittee" is safe).
**Every applied and rejected edit is recorded in `out/<slug>.ledger.md`** (grouped: notation /
author corrections / extraction artifacts / flagged-for-review) for you to vet before any audio is
paid for; the IR keeps the verbatim original and every call is cached. Disable the whole stage with
`--no-script-repair`.

### Phase 4 — Pre-TTS QC loop (audit → fix → confirm)

A **bounded** loop, capped at one fix. The phase-3 writer already did one Sonnet fix pass, so this
is: **Opus sweep → Sonnet fix → Opus confirm**.

1. **Audit / sweep** (`--verifier-model`, Opus by default) — flag red flags the **pipeline**
   introduced (leaked markup, code/garble read aloud, truncated sentences, a number voiced wrong, a
   reference number left unread). The sweep is Opus because it catches leaked citation numbers the
   cheaper model misses. It does **not** flag the author's own spelling, grammar, name
   pronunciation, or cross-reference numbers, nor the intended genericized/absent citations — those
   are correct.
2. **Fix** (`--llm-model`, Sonnet by default) — if flags remain, one pass turns them into safe
   find/replace edits (whole-token, minimal-edit, logged to the ledger).
3. **Confirm** (`--verifier-model`, Opus) — re-audit **once**. Its flags are final.

Cost is bounded: a clean script costs one Opus sweep; a defective one adds a Sonnet fix + a single
Opus confirm — no further iteration, everything cached (audit vs confirm keyed separately so they
do not collide). Disable the fix+confirm with `--no-qc-loop`, which falls back to a single cheap
read-only audit on `--llm-model`. The report lands at `out/<slug>.script-qc.md`. With
`--tts elevenlabs`, **high-severity flags block the render** (override with `--force`).

### Phase 5 — Render + assemble

ElevenLabs renders the (content-addressed cached) chunks; ffmpeg muxes the chaptered file.

```bash
export ANTHROPIC_API_KEY=...
export ELEVENLABS_API_KEY=...
export ELEVENLABS_VOICE_ID=...     # a real voice id (or pass --voice)

uv run audiobook run sample/your-thesis.pdf \
  --markdown out/your-thesis.cleaned.md \
  --llm anthropic --tts elevenlabs --cover cover/cover01.png --format mp4
```

Outputs land in `out/`: the chaptered audio (`.m4b` or `.mp4`) **plus** a whole-book `.mp3`
(`--format mp3` emits only that), the `.script.md`, the `.structure.md`, the
`.script-qc.md`, the `.chunks.json` plan, a `.provenance.json` sidecar (audio timestamp ->
source block id), `.qa.md` (the curator's decisions), and **`.ledger.md`** (see below). A cover
image shows for the whole runtime in the `.mp4` and embeds as album art in the `.m4b`/`.mp3`;
omit it for audio-only.

## Live progress (status spinner)

During a real run, `audiobook run` shows a one-line spinner on stderr under each phase header,
so you can see which stage or agent loop is working and for how long:

```
Phase 4: pre-TTS QC loop (audit -> fix -> Opus confirm) ...
⠹ QC confirm (Opus) (14s)
```

It cycles through the live step: `Script repair round 1/3`, each stage name, and the QC loop's
`QC audit (Opus)` -> `QC fix (Sonnet)` -> `QC confirm (Opus)`, with elapsed seconds so a long
LLM call clearly looks alive rather than hung. The line erases itself before each printed summary
line, so the deliverable output on stdout is unchanged.

The spinner is purely cosmetic and **only renders in an interactive terminal**. Piped, redirected,
or CI runs (stderr is not a TTY) are silent, so logs stay clean; `--dry-run` never animates. Run
the command directly (not through a pipe) to see it. In-process PDF parsing (`--parser
marker/mineru`) prints its own progress bars to stderr and will interleave with the spinner; the
recommended separate-parse then `--markdown` flow avoids that.

## The update ledger

`out/<slug>.ledger.md` is one reviewable record of every **judgment** the model-driven stages
made beyond plain text rendering: the structure inferred (chapters detected, back matter skipped,
Structurer reclassifications), the curator's pronunciation plan, and the auto-repairs applied or
rejected by the writer+auditor loop. The pipeline leans on the LLM to absorb per-thesis
variability rather than a growing pile of per-thesis regexes; the ledger is the accountability for
that, so you can vet every change before paying for audio. Chapter detection keys on the universal
`CHAPTER N` divider (so a thesis that numbers its sections `# 1`, `# 2` is not mis-split into
chapters), and an `APPENDIX` heading sends the rest of the document to skipped back matter.

## `run` options

| Flag | Meaning |
|---|---|
| `--markdown <path>` | ingest a pre-parsed Marker/MinerU markdown file (sets `--parser markdown`) |
| `--parser poppler\|marker\|mineru\|markdown` | PDF parser; poppler is offline, markdown ingests phase-1 output |
| `--llm mock\|anthropic` | structurer + cartographer + curator + citation genericizer + repair + QC (anthropic costs money) |
| `--llm-model <id>` | Anthropic model for the pipeline stages (default `claude-sonnet-4-6`; `claude-opus-4-8` for max quality) |
| `--verifier-model <id>` | model for the phase-4 QC **sweep + confirm** passes (default `claude-opus-4-8`; 1 call if clean, 2 if a fix runs) |
| `--no-qc-loop` | skip the QC fix+confirm loop (read-only audit only) |
| `--tts mock\|elevenlabs` | speech synthesis (elevenlabs costs money; needs ffmpeg) |
| `--format m4b\|mp4\|mp3` | chaptered file (m4b/mp4) + a whole-book mp3; `mp3` emits only the mp3 |
| `--cover <path>` | cover image (default `cover/cover01.png`); omit to render audio-only |
| `--voice <id>` | ElevenLabs voice id (or set `ELEVENLABS_VOICE_ID`) |
| `--profile committee\|general` | listener profile (see below) |
| `--preview` | render the first chapter only, with the cheap flash model |
| `--no-structure-eval` | skip the cartographer (use deterministic structure detection) |
| `--no-structurer` | skip the LLM block-kind classifier (then deterministic types stand alone) |
| `--no-curate` | skip the LLM pronunciation curator |
| `--no-script-repair` | skip the guarded auto-repair (safe pronunciation fixes) |
| `--as-written` | strict faithful mode: vocalize notation only; do NOT fix the author's typos/grammar or extraction artifacts (copy-edit is on by default) |
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
retune without touching code. Both profiles announce equations by number and discard citation
machinery; they differ on tables: `committee` (default) summarizes tables (LLM); `general`
skips them.

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

## The eval harness (generalization gate)

Unit and golden tests prove a transform is correct on a fixed input. They do not measure whether the
pipeline *generalizes* across theses - the thing that actually breaks when a new thesis arrives. The
eval harness fills that gap: it scores a produced spoken script against per-thesis ground-truth
labels, per dimension, so "does it work on a new thesis" becomes a number.

```bash
uv run python -m eval.run        # score the committed corpus -> eval/scorecard.md (offline, free)
```

- `eval/score.py` - pure scorers, architecture-agnostic (they grade *output vs labels*, never how it
  was produced): structure (chapters detected vs real count), citation/markup strip (labeled leak
  fingerprints absent), value preservation (labeled values survive), raw-token leak
  (`FORBIDDEN_RAW_TOKENS`, with SSML control tags stripped first).
- `eval/corpus/<id>/` - `labels.json` (ground truth) + `result.json` (chapters detected) + a
  `script.md` snapshot. Seeded with Gao and Zhu.
- The committed `eval/scorecard.md` is the **v1 baseline**: Gao parses cleanly (1.0 on every
  dimension); Zhu fails three of four (0 of 6 chapters detected, markup read aloud, a lost constant).
  That contrast is the "treadmill" quantified, and the bar the **v2 engine** (`run-v2`) was built to
  beat — now validated across Gao, Zhu, and Jain (faithfulness ~0.96-0.995). The verifier that gates
  v2 narration is the same code the faithfulness scorer reuses.
  `tests/unit/test_eval_score.py` pins the baseline numbers so a drift fails the normal suite.

To score a new thesis: produce its script (`audiobook run ... --llm anthropic --tts mock`), copy it
to `eval/corpus/<id>/script.md`, write its `labels.json` + `result.json`, and re-run.

See [CLAUDE.md](CLAUDE.md) and [specs/](specs/) for the architecture and conventions.
