# Thesis-to-Audiobook: Build Spec (engineering)

**Audience:** the coding agent (and humans) maintaining this project.
**Companion doc:** [thesis_audiobook_pipeline_plan.md](thesis_audiobook_pipeline_plan.md) is the
functional spec (what each stage does). This is the engineering spec (how it is built and kept
testable). When the two disagree: the functional spec wins on behavior, this one wins on structure
and testing.

**Status:** the original M0-M5 build order (plus an M6 cartographer) is complete and green, and the
pipeline has been validated end to end on full theses (Jain ~360pp; Gao). Since then it has grown a
markdown-ingestion path, an LLM **structurer**, a two-pass **extraction repair**, a bounded
**pre-TTS QC loop**, an author **copy-edit** stage with deterministic claim-safety guards, and a
live status spinner. This doc describes the project as it stands; section 13 records the build
history. `CLAUDE.md` points here and stays in the agent's working context.

---

## 1. Non-negotiables

1. **Typed everywhere.** Pyright strict on `src`. The IR is Pydantic v2 with `extra="forbid"`, so a
   stage that emits a malformed IR fails fast at the boundary, not silently downstream.
2. **No test spends money or hits a network by default.** External services are behind ports and
   replaced with mocks in tests. An autouse cost guard (section 7) makes any real Anthropic or
   ElevenLabs call raise. Live tests are opt-in (`pytest -m live`).
3. **Pure core, effectful edge.** Deterministic transforms contain zero I/O. All I/O (PDF parsing,
   LLM, TTS, ffmpeg, filesystem, cache, the status spinner) lives in adapters behind ports, or in
   the CLI composition root. A file under `stages/` or `normalization/` that imports an SDK,
   `httpx`/`requests`, or touches the filesystem is a bug.
4. **Deterministic and reproducible.** Seeded, content-addressed caching, pinned model ids, a
   version string per LLM stage in its cache key. Same input plus same config yields the same script
   byte-for-byte.
5. **Never silently guess (claim-safety).** The LLM never writes spoken prose from scratch. Every
   model-driven stage emits only labels, enums, or `find -> replace` edits; deterministic code does
   the rendering, and a deterministic guard validates risky edits (section 9). Structural ambiguity
   is collected as typed warnings on the `WarningsSink` and surfaced at a review gate / the ledger,
   not papered over.
6. **Prose and comments: no em dashes.**

---

## 2. Architecture: ports and adapters

The domain (the IR plus the stages) is pure and depends only on **ports** (Protocols). The outside
world is **adapters**. Tests inject mocks, so the whole pipeline runs offline, fast, and free.

| Port (`ports/`) | Responsibility | Real adapters | Mock |
|---|---|---|---|
| `PdfParser` (`parser.py`) | source to structured blocks | `MarkerParser`, `MinerUParser`, `PopplerParser`, `MarkdownFileParser` | `MockParser` (fixed parse of a tiny fixture) |
| `LlmClient` (`llm.py`) | structure/curation/repair/QC; `complete(prompt, *, system, max_tokens)` | `AnthropicClient` | `MockLlm` (deterministic, letters-only) |
| `TtsClient` (`tts.py`) | text to audio bytes | `ElevenLabsClient` | `MockTts` (silent WAV, deterministic length) |
| `PronunciationPublisher` (`pronunciation.py`) | publish a pronunciation dictionary | `ElevenLabsPronunciation` | `MockPronunciation` |
| `AudioMuxer` (`audio.py`) | concat + chapterize + cover | `FfmpegMuxer` | `MockMuxer` |
| `Cache` (`cache.py`) | content-addressed byte store | `FileCache` | `MemoryCache` |
| `StatusReporter` (`reporter.py`) | ephemeral terminal progress | `TerminalReporter` (isatty-gated spinner) | `NoopReporter` (Context default) |

There is **no** `BibParser`/GROBID: in-text citations are treated as machinery (stripped and
genericized), so no bibliography is parsed (see the functional spec). Stages receive their ports
through a `Context` object (`context.py`); they never import adapters. The composition root
(`bootstrap.py` + `cli.py`) wires real vs mock adapters.

---

## 3. Project layout

```
thesis-audiobook/
  pyproject.toml              # uv-managed; ruff, pyright, pytest config
  CLAUDE.md                   # points here + the functional spec
  specs/                      # this file + the functional spec
  src/thesis_audiobook/
    ir.py                     # Pydantic models: Block, Document, Region, StructureMap, Chunk...
    pipeline.py               # Stage protocol + Pipeline runner (frm/to slicing)
    context.py                # Context: config + ports + logger + warnings + status reporter
    config.py                 # typed Config + Profile (TOML data files)
    bootstrap.py              # build_context / build_mock_context (composition root)
    warnings.py               # typed LowConfidence warnings + report
    log.py                    # minimal structured logger (stderr)
    cost.py provenance.py     # cost estimate; audio-timestamp -> block-id sidecar
    cli.py                    # Typer app
    markdown_ir.py            # Marker/MinerU markdown -> Document (the ingestion path)
    cleanup.py                # deterministic build_ir text cleanup helpers
    # --- LLM-stage logic (pure: prompt build + parse + apply; the call lives in the stage) ---
    structurer.py cartographer.py curate.py            # block-kind / structure map / pronunciation
    citation_naturalize.py                             # strip markers + genericize mentions
    extraction_repair.py extraction_qc.py qc_fix.py    # phase-2 repair + phase-4 QC fix
    script_repair.py copyedit.py                       # the writer + the copy-edit guard
    script_qc.py ledger.py                             # phase-4 QC report + the update ledger
    chunking.py                                        # pure chunk planner
    stages/                   # one module per stage; pure or port-mediated, never import adapters
      ingest.py build_ir.py structurer.py cartographer.py select.py curate.py
      math.py figures.py citations.py normalize.py appendix_signpost.py
      assemble_script.py script_repair.py script_qc.py lexicon.py tts.py assemble_audio.py
    normalization/            # pure rules engine, no I/O, the most-tested code
      numbers.py units.py stats.py acronyms.py greek.py latex.py
      mojibake.py repetition.py segmentation.py
    ports/                    # Protocols only (see section 2)
    adapters/                 # real adapters + mocks.py + status.py
    data/                     # pronunciation.json + profiles/{committee,general}.toml
  tests/
    conftest.py               # shared fixtures + autouse cost guard
    fixtures/                 # tiny.ir.json, golden IR, cassettes
    unit/ property/ golden/ integration/   # integration = @pytest.mark.live / contract
```

Rule of thumb: if a file under `normalization/` or `stages/` imports an SDK, `httpx`, or touches
the filesystem, that is a bug. Move the I/O to an adapter; keep the prompt/parse/apply pure.

---

## 4. The IR as a typed contract

Pydantic v2, `StrictModel` (`extra="forbid"`). Stages populate `spoken`, `handling`, `keep`, and the
document-level `script` and `chunks`; **they never overwrite `text`** (the verbatim source is the
provenance anchor). Validation runs at every stage boundary.

Key models (`ir.py`):
- `Block` - `id, type (BlockType), chapter, section, page, text, spoken, keep, handling (Handling),
  refs, latex, confidence, notes`. `current_text()` returns `spoken` if set else `text`.
- `Document` - `meta (DocumentMeta), blocks, figures, equations, tables`, plus the derived `script`
  and `chunks` (populated by `assemble_script`). There is **no** `citations`/`bibliography` map.
- `Region` / `StructureMap` - the cartographer's claim-safe output: each `Region` is a `RegionKind`
  + `RegionDecision` (include/skip/review) + EXISTING block-id span + confidences + a `label`/
  `rationale` that appear ONLY in the structure.md artifact, never spoken. The cartographer cannot
  inject audio by construction.
- `Chunk` - one TTS unit with `block_ids` provenance and `prev_id`/`next_id` neighbor pointers.

---

## 5. Stage protocol and pipeline runner

Every stage is a small object with a `name` and `run(doc, ctx) -> doc`, so stages are independently
testable and composable.

```python
class Stage(Protocol):
    name: str
    def run(self, doc: Document, ctx: Context) -> Document: ...

class Pipeline:
    def run(self, doc, ctx, *, frm=None, to=None) -> Document:
        for stage in self._slice(frm, to):
            ctx.status.update(stage.name)          # ephemeral progress (no-op off-TTY/in tests)
            doc = stage.run(doc, ctx)
            doc = Document.model_validate(doc.model_dump())   # boundary validation
            ctx.log.info("stage_done", stage=stage.name, blocks=len(doc.blocks))
        return doc
```

Default stage order (`stages/__init__.py`): `ingest, build_ir, structurer, cartographer, select,
curate, math, figures, citations, normalize, appendix_signpost, assemble_script, script_repair,
script_qc, lexicon, tts, assemble_audio`. `frm=`/`to=` let the CLI run a slice (the CLI brackets
phase 3 = ...→`script_repair`, phase 4 = `script_qc`, phase 5 = `lexicon`→end).

---

## 6. Ports and mocks

Ports are Protocols; mocks are deterministic. `MockTts` returns a silent WAV whose duration is a
function of `len(text)`, so audio assembly is testable without a voice. `MockLlm` returns
letters-only deterministic text keyed by the prompt hash, so it survives the normalizer unchanged
and every LLM stage degrades to a no-op offline. `NoopReporter` is the Context default for `status`,
so tests and `--dry-run` stay byte-for-byte silent.

---

## 7. Testability strategy (the core of this spec)

### 7.1 Deterministic / effectful split

| Category | Modules | Test approach | Coverage |
|---|---|---|---|
| Pure transforms | `normalization/*`, `copyedit`, `citation_naturalize`, `chunking`, `script_repair`/`extraction_repair`/`script_qc` (prompt+parse+apply+guards), `ledger`, `cost`, `provenance` | unit + property + golden, offline | high |
| Port-mediated stages | every `stages/*` (LLM/TTS/parse via mocks) | unit with mock ports; contract test vs cassette | high |
| Adapters | `adapters/*` | contract tests vs recorded cassettes; thin `live` suite | best effort |

### 7.2 Cost and network guard (autouse)

`tests/conftest.py` patches the real `AnthropicClient.complete`, `ElevenLabsClient.synthesize`, and
`ElevenLabsPronunciation.publish` to raise in any non-`live` test, so an accidental live call fails
loudly. Run live tests only with `pytest -m live` and real keys. CI never runs them.

### 7.3 Golden / snapshot tests (syrupy)

The IR at stage boundaries and the final script are serialized to committed golden files; an
end-to-end golden runs the full pipeline on the tiny fixture with all-mock adapters and diffs the
script. This is the cheap regression net; regenerate intentionally with the syrupy update flag.

### 7.4 Property-based tests (hypothesis)

- **Normalizer idempotency:** `normalize_all(normalize_all(x)) == normalize_all(x)`.
- **No-leak invariant:** after normalization the spoken text contains none of
  `FORBIDDEN_RAW_TOKENS` (`%`, `±`, `^`, `_`, bare `μ`, `<`, `>`, citation brackets).
- **Chunk planner conservation:** concatenating chunk texts reproduces the script; every chunk is
  under the limit; neighbor pointers are consistent.
- **Cache keying:** identical inputs yield identical keys; changing any field changes the key.

### 7.5 Fixtures

`tests/fixtures/tiny.ir.json` (the golden IR the `MockParser` returns), the golden chapter6 IR +
script, a small plant-physiology pronunciation lexicon, and `cassettes/` (recorded parser/LLM
interactions) so contract tests run offline.

---

## 8. CLI surface (Typer)

Commands map to phases and gates, so a human (or a test) can run any slice.

```
audiobook run INPUT.pdf [--markdown CLEAN.md] [--llm anthropic] [--tts mock|elevenlabs] ...
audiobook parse INPUT.pdf -o ir.json                  # phases 1-2 -> IR JSON
audiobook check-extraction  MARKER.md --llm anthropic # audit the raw markdown (read-only)
audiobook repair-extraction MARKER.md --llm anthropic # two-pass guarded cleanup + de-shred -> *.cleaned.md
# script / render / assemble are thin stubs that point at `run` (superseded).
```

Key `run` flags: `--dry-run` (cost + chunk plan, zero external calls), `--preview` (first chapter,
flash model), `--parser poppler|marker|mineru|markdown`, `--markdown PATH` (ingest pre-parsed
markdown; sets `--parser markdown`), `--llm mock|anthropic`, `--llm-model`, `--verifier-model`,
`--no-qc-loop`, `--tts mock|elevenlabs`, `--format m4b|mp4|mp3`, `--cover`, `--voice`, `--profile`,
`--no-structurer`, `--no-structure-eval`, `--no-curate`, `--no-script-repair`, `--as-written`
(strict notation-only, copy-edit off), `--no-script-qc`, `--force` (render past a HIGH QC flag).

---

## 9. Claim-safety: constrained LLM output + deterministic guards

This is the architectural heart and the reason the LLM cannot hallucinate narration.

- **Constrained output.** Every model-driven stage returns a typed, restricted shape: the
  structurer returns a block-kind per id; the cartographer returns `Region`s (enums + existing
  block-id spans); the curator returns a pronunciation plan mapping each term to one form; the
  citation genericizer maps each author mention to one phrase from a FIXED set; the writer / QC fixer
  / extraction repair return `find -> replace` edits. Deterministic code renders from these.
- **Edit application is whole-token.** `apply_one` replaces only on word boundaries, so a unit fix
  (`mm` -> "millimeters") can never rewrite the inside of a word ("co**mm**ittee" is safe).
- **The copy-edit guard** (`copyedit.py` `copyedit_guard`) is the floor for author-text edits
  (spelling/grammar/spacing/readability). An edit is applied only if it preserves every VALUE
  (digits AND spelled-out numbers/units/connectives/Greek variable names, in order), every POLARITY
  word, and every DIRECTIONAL result word ("increased"/"higher"/"positive"/"above"), changing at
  most one content word in place (function words may be added/removed freely; a pure-whitespace edit
  is always allowed). It replaced an LLM faithfulness auditor that over-blocked. The author's data
  and claims are never auto-changed - a suspected number/sign error is flagged, not edited.
- **The artifact guard** (`extraction_repair.py` `is_faithful_artifact`) is the floor for phase-2
  re-renders of Marker-shredded notation. After stripping markup tags from both sides it requires
  the ordered digits identical, every value symbol (`± ° % × ÷ = / -`) count-exact, and no NEW
  letter introduced - so a faithful re-render passes while inventing/dropping/reordering a value or
  swapping a variable is rejected.
- **The pre-TTS QC loop** (`stages/script_qc.py`): an Opus **audit/sweep** finds pipeline defects in
  the finished script; if any, ONE Sonnet **fix** pass turns flags into guarded find/replace edits;
  a single Opus **confirm** re-audits. Flags whose `location` is not a verbatim substring of the
  script are dropped (the honesty filter). HIGH-severity flags gate the billed render.
- **Accountability.** Everything the model-driven stages decide is written to
  `out/<slug>.ledger.md` (structure, pronunciation, citation genericizations, applied/rejected
  edits, grouped by kind) so a human vets it before any spend. The IR `text` field stays verbatim.

---

## 10. Config and profiles

Typed `Config` (`config.py`). Profiles are validated TOML data files
(`data/profiles/{committee,general}.toml`), loaded by `profile_for()`, with code-level fallbacks.
Secrets come only from the environment and never enter the IR, logs, or cache keys.

`Profile`: `equation_tier` (announce | full; default announce - equations are announced by number,
never LLM-glossed, because the gloss hallucinated), `table_handling` (skip | summarize),
`include_appendices`, `voice_id`, `model_id` (`eleven_multilingual_v2`) + `preview_model_id`
(flash), `voice_settings`, `output_format`, `apply_text_normalization` (default off). There is **no**
`citation_policy` (citations are always discarded/genericized).

`Config` toggles (all default on): `structurer`, `structure_eval` (cartographer), `curate`,
`script_repair`, `copyedit`, `script_qc`, `qc_loop`; models `llm_model` (Sonnet, the pipeline
stages) and `verifier_model` (Opus, the QC sweep/confirm); `parser_backend`, `markdown_path`,
`output_mode`, `chunk_char_limit`, `usd_per_character`, `cache_dir`, `seed`.

---

## 11. Determinism and caching

- Content-addressed TTS cache: key = `sha256(text, voice_id, model_id, voice_settings,
  output_format, apply_text_normalization, seed, previous_text, next_text, dict_version)`. A script
  edit invalidates only the touched chunk plus its two neighbor seams.
- Each LLM stage caches its response under a key that includes a VERSION string (e.g.
  `scriptrepair-v5`, `scriptqc-v5`, `extrepair-v2`, `curate-v*`, `cite-generic-v2`) plus the
  `type(llm).__name__` and the content hash - so bumping a prompt forces a clean re-derivation, and
  re-running unchanged markdown reuses results with no billing. Empty/garbled LLM responses are
  never cached (so the offline mock and transient failures re-check next run).

---

## 12. Error handling philosophy

- Domain code raises typed errors and never retries; retries/backoff live in adapters only. Real
  adapter failures surface as `AnthropicUnavailableError` / `ElevenLabsUnavailableError` /
  `FfmpegUnavailableError`, which the CLI turns into a clean exit.
- Low-confidence findings are data, not exceptions: a `WarningsSink` collects
  `LowConfidence(block_id, reason, score)`; the CLI prints them at the gate (e.g. a capitalized
  citation strip is warned, never silently deleted).
- Validation at every boundary: a malformed transform fails in its own stage's test.

---

## 13. Build history (the sequence the project was built in)

- **M0 walking skeleton** - IR, Stage protocol, Pipeline runner, all ports, mock adapters, the tiny
  fixture, `run` end-to-end on mocks. *Green.*
- **M1 deterministic core** - `normalization/*`, select, figures, citations, assemble_script, the
  chunk planner; full unit/property/golden coverage. *Green.*
- **M2 parsing** - real Marker/MinerU/poppler parsers and `build_ir` cleanup (de-hyphenation,
  ligatures, reflow, header/footer strip, region tagging) with Gate A warnings; cassette contract
  tests. *Green.*
- **M3 LLM stages** - `AnthropicClient`; equation handling (announce, after the gloss was found to
  hallucinate) and table summary; mocked in tests, one cassette contract test. *Green.*
- **M4 TTS + assembly** - `ElevenLabsClient`, `FileCache`, `FfmpegMuxer`, the cost estimator,
  preview, provenance sidecar, cover art + dual output (chaptered file + whole-book mp3). *Green.*
- **M5 hardening** - TOML profiles, pronunciation publish, structured logging. *Green.*
- **M6 cartographer** - the LLM structure map (claim-safe regions) that rescues non-standard thesis
  structure; validated on the full Jain thesis via Marker -> markdown ingestion. *Green.*
- **Post-M6 (this era).** Markdown-ingestion path (`MarkdownFileParser`, `--markdown`) so Marker can
  run isolated; the **structurer** (LLM block-kind classifier); two-pass **extraction repair**
  (`repair-extraction`) with the artifact de-shredding guard; the bounded **pre-TTS QC loop**; the
  author **copy-edit** stage + `copyedit_guard` (NotebookLM-style listenability without altering
  claims); the **update ledger**; and the live **status spinner** (`StatusReporter`). Each landed
  with an adversarial review of its guards and full suite/lint/type green.

**Definition of done (per change):** ruff clean; `pyright` 0 errors on `src`; offline suite green;
goldens unchanged or intentionally updated; no test triggered a live call; any new regex/guard
adversarially reviewed before shipping.
