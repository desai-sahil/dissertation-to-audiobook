# Thesis-to-Audiobook: Build Spec for the Coding Agent

**Audience:** the Claude coding agent that will implement this project.
**Companion doc:** `pipeline_plan.md` is the functional spec (what each stage does). This doc is the engineering spec (how to build it well and testably). When the two disagree on behavior, `pipeline_plan.md` wins; on structure and testing, this doc wins.
**How to use:** drop this in as `docs/BUILD_SPEC.md` and reference it from `CLAUDE.md` so it stays in the agent's working context. Build in the milestone order in section 13. Do not start stage logic before the walking skeleton in M0 is green.

---

## 1. Non-negotiables

1. **Typed everywhere.** Pyright or mypy in strict mode. The IR is Pydantic v2. A stage that emits a malformed IR fails fast in tests, not silently downstream.
2. **No test spends money or hits a network by default.** External services are behind ports and replaced with mocks in tests. A cost guard (section 7) makes accidental live calls raise.
3. **Pure core, effectful edge.** Deterministic transforms contain zero I/O. All I/O (parsing, LLM, TTS, filesystem, cache) lives in adapters behind ports.
4. **Deterministic and reproducible.** Seeded, content-addressed caching, pinned model ids. Same input plus same config yields the same script byte-for-byte.
5. **Never silently guess.** Structural ambiguity (broken reading order, unlinked citations above threshold) is collected as typed warnings and surfaced at a review gate, not papered over.

---

## 2. Architecture: ports and adapters

The domain (the IR plus the stages) is pure and depends only on **ports** (abstract protocols). The outside world is **adapters** that implement those ports. Tests inject mock adapters, so the entire pipeline runs offline, fast, and free.

Ports to define:

| Port | Responsibility | Real adapters | Mock |
|---|---|---|---|
| `PdfParser` | PDF to structured blocks | `MarkerParser`, `MinerUParser` | `MockParser` (returns a fixed parse of the tiny fixture) |
| `BibParser` | bibliography + citation linkage | `GrobidClient` | `MockBibParser` |
| `LlmClient` | equation gloss, table summary | `AnthropicClient` | `MockLlm` (canned glosses keyed by input hash) |
| `TtsClient` | text to audio bytes | `ElevenLabsClient` | `MockTts` (emits silent or tone WAV of deterministic length) |
| `Cache` | content-addressed store | `FileCache` | `MemoryCache` |

Stages receive their ports through a `Context` object (dependency injection), never import adapters directly.

---

## 3. Project layout

```
thesis-audiobook/
  pyproject.toml              # uv-managed; ruff, pyright, pytest config live here
  CLAUDE.md                   # points the agent at docs/BUILD_SPEC.md
  src/thesis_audiobook/
    ir.py                     # Pydantic models: Document, Block, Figure, Equation, Citation...
    pipeline.py               # Stage protocol + Pipeline runner
    context.py                # Context (config + ports + cache + logger + warnings sink)
    config.py                 # typed config + profile loading/validation
    warnings.py               # typed LowConfidence warnings + report
    stages/                   # one module per pipeline stage; all pure or port-mediated
      ingest.py  build_ir.py  select.py  math.py  figures.py
      citations.py  normalize.py  assemble_script.py  lexicon.py
      tts.py  assemble_audio.py
    normalization/            # pure rules engine, no I/O, the most-tested code
      numbers.py  units.py  stats.py  acronyms.py  segmentation.py  greek.py
    ports/                    # Protocols only
      parser.py  bib.py  llm.py  tts.py  cache.py
    adapters/
      marker_parser.py  mineru_parser.py  grobid_client.py
      anthropic_llm.py  elevenlabs_tts.py  file_cache.py
      mocks.py                # all mock adapters in one place
    cli.py                    # Typer app
  tests/
    conftest.py               # shared fixtures + autouse cost guard
    fixtures/
      tiny_thesis.pdf         # synthetic 3-page thesis, the workhorse fixture
      tiny_thesis.ir.json     # golden IR for the fixture
      lexicon.json
      cassettes/              # recorded parser/LLM/TTS interactions
    unit/                     # one file per pure module
    property/                 # hypothesis tests
    golden/                   # snapshot tests of IR boundaries and final script
    integration/              # @pytest.mark.live, skipped unless --live
  docs/
    pipeline_plan.md
    BUILD_SPEC.md             # this file
```

Rule of thumb: if a file under `normalization/` or `stages/` imports `requests`, `httpx`, an SDK, or touches the filesystem, that is a bug. Move the I/O to an adapter.

---

## 4. The IR as a typed contract

Pydantic v2 models. Stages populate `spoken`, `handling`, `keep`; they never overwrite `text`. Validation runs at every stage boundary so a broken transform is caught immediately.

```python
# ir.py (skeleton)
from enum import StrEnum
from pydantic import BaseModel

class BlockType(StrEnum):
    paragraph = "paragraph"; heading = "heading"
    figure_caption = "figure_caption"; table = "table"
    equation_display = "equation_display"; equation_inline = "equation_inline"
    footnote = "footnote"; reference_list = "reference_list"
    frontmatter = "frontmatter"; backmatter = "backmatter"; code = "code"

class Handling(StrEnum):
    speak = "speak"; skip = "skip"; gloss = "gloss"
    summarize = "summarize"; announce = "announce"

class Block(BaseModel):
    id: str
    type: BlockType
    chapter: int | None = None
    section: str | None = None
    page: int | None = None
    text: str
    spoken: str | None = None
    keep: bool = True
    handling: Handling = Handling.speak
    refs: list[str] = []
    latex: str | None = None
    confidence: float = 1.0
    notes: list[str] = []

class Document(BaseModel):
    meta: dict
    blocks: list[Block]
    figures: dict[str, "Figure"] = {}
    equations: dict[str, "Equation"] = {}
    tables: dict[str, "Table"] = {}
    citations: dict[str, "Citation"] = {}
    bibliography: dict[str, "BibEntry"] = {}
```

The `tiny_thesis.ir.json` golden file is the canonical example and the anchor for most tests.

---

## 5. Stage protocol and pipeline runner

Every stage is a small object with a `name` and a `run(doc, ctx) -> doc`. This makes stages independently testable (feed a Document, assert the returned Document) and composable.

```python
# pipeline.py (skeleton)
from typing import Protocol
from .ir import Document
from .context import Context

class Stage(Protocol):
    name: str
    def run(self, doc: Document, ctx: Context) -> Document: ...

class Pipeline:
    def __init__(self, stages: list[Stage]): self.stages = stages
    def run(self, doc: Document, ctx: Context, *, frm: str | None = None, to: str | None = None) -> Document:
        for stage in self._slice(frm, to):
            doc = stage.run(doc, ctx)
            Document.model_validate(doc.model_dump())  # boundary validation
            ctx.log.info("stage_done", stage=stage.name, blocks=len(doc.blocks))
        return doc
```

`--from-stage` and `--to-stage` let the agent and the user re-run a single stage against a saved IR, which is also how golden tests target individual stages.

---

## 6. Ports and mocks

Ports are Protocols; mocks are deterministic.

```python
# ports/tts.py
from typing import Protocol
class TtsRequest(BaseModel):
    text: str; voice_id: str; model_id: str
    previous_text: str | None = None; next_text: str | None = None
    seed: int | None = None; dictionary_ids: list[str] = []
class TtsClient(Protocol):
    def synthesize(self, req: TtsRequest) -> bytes: ...

# adapters/mocks.py
class MockTts:
    """Returns a deterministic silent WAV sized from len(text). Never networks."""
    def synthesize(self, req: TtsRequest) -> bytes:
        return silent_wav(seconds=len(req.text) / 15.0)
```

The mock TTS encodes a useful invariant for tests: output duration is a deterministic function of input length, so the audio-assembly stage can be tested without a real voice.

---

## 7. Testability strategy (the core of this spec)

### 7.1 The deterministic / effectful split

| Category | Modules | Test approach | Coverage target |
|---|---|---|---|
| Pure transforms | `normalization/*`, `citations`, `figures`, `select`, `assemble_script`, chunk planner | unit + property + golden, all offline | 95%+ |
| Port-mediated stages | `ingest`, `math`, `tts`, `assemble_audio` | unit with mock ports; contract test against cassette | 85%+ |
| Adapters | `adapters/*` | contract tests vs recorded cassettes; thin live suite behind `--live` | best effort |

### 7.2 Cost and network guard (autouse)

No test may hit ElevenLabs or the LLM unless explicitly marked `live`. Enforce it:

```python
# conftest.py
@pytest.fixture(autouse=True)
def _no_live_calls(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return  # opt-in live tests may proceed
    def boom(*a, **k): raise RuntimeError("live external call in a non-live test")
    monkeypatch.setattr("thesis_audiobook.adapters.elevenlabs_tts.ElevenLabsClient.synthesize", boom)
    monkeypatch.setattr("thesis_audiobook.adapters.anthropic_llm.AnthropicClient.complete", boom)
```

Run live tests only with `pytest -m live` and real keys present. CI never runs them.

### 7.3 Golden / snapshot tests

Serialize the IR at each stage boundary and the final script to committed golden files. A `--update-goldens` flag (or `syrupy`) regenerates them on intentional changes. The end-to-end golden runs the full pipeline on `tiny_thesis.pdf` with all-mock adapters and diffs the resulting script. This is your cheap regression net.

### 7.4 Property-based tests (hypothesis)

Encode the behaviors that matter most as invariants, not examples:

- **Normalizer idempotency:** `normalize(normalize(x)) == normalize(x)`.
- **No-leak invariant:** after normalization, the spoken text contains none of the forbidden raw tokens (`%`, `±`, `^`, `_`, bare `μ`, `<`, `>`, citation brackets). This is the testable form of "do not mangle notation."
- **Chunk planner conservation:** concatenating all chunk texts reproduces the script exactly (nothing dropped or duplicated), and every chunk is under the character limit, and neighbor pointers are consistent.
- **Cache keying:** identical inputs yield identical keys; changing any input field (text, voice, model, settings, dict version) changes the key.

### 7.5 Fixtures

- `tiny_thesis.pdf`: a hand-built three-page synthetic thesis containing one figure with caption, one display equation, one inline `gs`, one table, two citations (one numeric, one author-year), front matter (title, TOC), and a bibliography. This single fixture exercises every stage.
- `tiny_thesis.ir.json`: the golden IR after `build_ir`.
- `lexicon.json`: a small plant-physiology lexicon (`gs`, `psi_xyl`, `slac1`, `WT`).
- `cassettes/`: recorded Marker, GROBID, LLM, and TTS interactions for the fixture, so adapter contract tests run offline.

### 7.6 Example tests

```python
# tests/unit/test_numbers.py
@pytest.mark.parametrize("raw,spoken", [
    ("37%", "thirty-seven percent"),
    ("p<0.05", "p less than zero point zero five"),
    ("5.2 ± 0.3", "five point two, plus or minus, zero point three"),
    ("2-8", "two to eight"),
])
def test_number_normalization(raw, spoken):
    assert normalize_numbers(raw) == spoken

# tests/property/test_no_leak.py
@given(st.text())
def test_no_raw_notation_leaks(s):
    out = normalize_all(s)
    assert not (set(out) & FORBIDDEN_RAW_TOKENS)
```

---

## 8. CLI surface (Typer)

Commands map to stages and gates, so a human (or a test) can run any slice.

```
audiobook parse INPUT.pdf -o ir.json            # Agent 1+2, writes IR
audiobook script ir.json -o script.md           # through Gate B, the reviewable script
audiobook render script.md -o audio/            # TTS, cached
audiobook assemble audio/ -o thesis.m4b         # build the audiobook
audiobook run INPUT.pdf --profile committee      # full pipeline
```

Global flags: `--profile {committee,general}`, `--from-stage`, `--to-stage`, `--preview` (first chapter only), `--dry-run` (no external calls, prints cost estimate and produces the script), `--seed`, `--update-goldens`.

`--dry-run` doubles as the cost estimator and is fully testable offline.

---

## 9. Config and profiles

Typed config via Pydantic Settings. Profiles are data files (`profiles/committee.toml`), loaded and validated, not code branches. Secrets (API keys) come from the environment only and are never written to the IR, logs, or cache keys.

```python
class Profile(BaseModel):
    name: str
    equation_tier: Literal["announce", "gloss", "full"] = "gloss"
    citation_policy: Literal["drop", "brief", "full"] = "brief"
    table_handling: Literal["skip", "summarize"] = "summarize"
    include_appendices: bool = False
    voice_id: str
    model_id: str = "eleven_multilingual_v2"
```

---

## 10. Determinism and caching

- Content-addressed cache: key = `sha256(text, voice_id, model_id, settings, seed, dict_version)`. `FileCache` stores audio bytes under that key. A script edit invalidates only the touched chunks.
- Pin `model_id` and dictionary version in the key so a model or pronunciation change forces a clean re-render.
- TTS chunks pass `previous_text` / `next_text` for prosody continuity; the cache key includes neighbors only if you decide boundary audio should change with context (flag this decision; default is to include them so edits to a neighbor refresh the seam).

---

## 11. Error handling philosophy

- **Domain code raises typed errors and never retries.** Retries and backoff live in adapters only.
- **Low-confidence findings are data, not exceptions.** A `WarningsSink` on the Context collects `LowConfidence(block_id, reason, score)` entries; the CLI prints a report at Gate A. Parsing never silently reorders or drops content above the confidence threshold without flagging it.
- **Validation at boundaries.** Every stage output is re-validated against the Pydantic schema, so a malformed transform fails in its own test rather than three stages later.

---

## 12. Dev tooling and quality gates

- **Packaging:** `uv` + `pyproject.toml`.
- **Lint/format:** `ruff` (lint + format).
- **Types:** `pyright` strict (or mypy strict).
- **Tests:** `pytest`, `pytest-cov`, `hypothesis`, `syrupy` (snapshots), `pytest-recording` or `vcrpy` (cassettes).
- **Hooks:** `pre-commit` running ruff, type check, and the fast unit suite.
- **CI (GitHub Actions):** ruff, type check, full offline test suite, coverage gate. Live tests excluded.

**Definition of done (per merge):** ruff clean; types clean; offline suite green; coverage gates met; end-to-end golden on `tiny_thesis` unchanged or intentionally updated; no test triggered a live call.

---

## 13. Build order (the agent builds in this sequence)

**M0 Walking skeleton.** Repo, `pyproject`, CI, the IR models, `Stage` protocol, `Pipeline` runner, all ports, all mock adapters, the `tiny_thesis` fixture, and a `run` command that executes the full pipeline end-to-end **on mocks** and writes a placeholder audio file. Prove the wiring before any real logic.
*Done when:* `audiobook run tiny_thesis.pdf --dry-run` runs through every stage on mocks and the end-to-end golden is committed.

**M1 Deterministic core.** Implement `normalization/*`, `citations`, `figures`, `select`, `assemble_script`, and the chunk planner. Full unit, property, and golden coverage. No real external calls anywhere.
*Done when:* property invariants in 7.4 pass; the script for `tiny_thesis` matches its golden.

**M2 Parsing adapters.** Real `MarkerParser` (and `MinerUParser` switch), `GrobidClient` with citation linkage, the `build_ir` cleanup (de-hyphenation, ligatures, reading order, header/footer strip), and Gate A warnings. Contract-tested with cassettes.
*Done when:* the real parse of `tiny_thesis.pdf` reconstructs the golden IR within tolerance; citation linkage at least 90%.

**M3 LLM stage.** Equation gloss and table summary via `LlmClient`, mocked in tests with canned outputs, one cassette-backed contract test.
*Done when:* `math` and `figures` stages produce glosses for the fixture under the `committee` profile, fully offline in tests.

**M4 TTS and assembly.** `ElevenLabsClient` (multilingual_v2, request stitching, pronunciation dictionary locators), `FileCache`, `assemble_audio` (M4B with chapter markers), `--dry-run` cost estimator, `--preview`.
*Done when:* the full pipeline renders `tiny_thesis` to an M4B using `MockTts` in tests; a single `--live` integration test renders one chunk against the real API.

**M5 Hardening.** Profiles wired through, lexicon publish to ElevenLabs, structured logging and provenance sidecar, docs.
*Done when:* both profiles produce distinct scripts on `tiny_thesis`; provenance map round-trips.

---

## 14. First task for the agent

Start M0. Create the repo skeleton in section 3, implement `ir.py`, `pipeline.py`, `context.py`, the five ports, the mock adapters, and the `tiny_thesis` fixture. Wire `audiobook run --dry-run` end-to-end on mocks. Commit the cost guard from 7.2 and one passing golden test before writing any stage logic. Do not implement real parsing, LLM, or TTS until M0 is green.
