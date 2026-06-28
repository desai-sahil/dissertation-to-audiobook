# CLAUDE.md

Thesis-to-Audiobook: a typed, testable pipeline that turns a PhD thesis PDF into a
navigable audiobook.

## Read these first

- Engineering spec (governs structure and testing): [specs/thesis_audiobook_build_spec.md](specs/thesis_audiobook_build_spec.md)
- Functional spec (governs stage behavior): [specs/thesis_audiobook_pipeline_plan.md](specs/thesis_audiobook_pipeline_plan.md)

When the two disagree: the functional spec wins on behavior, the engineering spec
wins on structure and testing.

## Conventions (non-negotiable)

1. Python 3.12+. Typed everywhere; pyright runs in strict mode.
2. The IR is Pydantic v2 (see src/thesis_audiobook/ir.py). Stages populate `spoken`,
   `handling`, `keep`, `script`, `chunks`; they never overwrite `text`.
3. The CLI is Typer (src/thesis_audiobook/cli.py).
4. Pure core, effectful edge. Deterministic transforms contain zero I/O. All I/O
   (PDF parsing, LLM, TTS, filesystem writes, cache) lives in adapters behind ports,
   or in the CLI composition root. If a file under stages/ or normalization/ imports
   an SDK, httpx/requests, or touches the filesystem, that is a bug.
5. Stages receive their ports through the Context object. They never import adapters.
6. Every stage output is re-validated against the Pydantic schema at the boundary,
   so a malformed transform fails fast in its own test.
7. No test spends money or hits a network by default. The autouse cost guard in
   tests/conftest.py makes any real ElevenLabs or LLM call raise. Live tests are
   marked `live` and run only with `pytest -m live`.
8. Determinism: same input plus same config yields the same script byte-for-byte.
   TTS chunks are content-addressed cached.
9. Never silently guess. Structural ambiguity is collected as typed warnings on the
   WarningsSink and surfaced at a review gate, not papered over.
10. Prose and comments: no em dashes.

## Build order

The build history is section 13 of the engineering spec. Milestones M0 to M6 (deterministic
core, parsing, LLM stages, TTS + assembly, hardening, cartographer), the post-M6 era
(markdown ingestion, structurer, extraction repair, QC loop, copy-edit, ledger), and the
**eval harness + v2 engine** are all green. The current engine is **v2** (vision-grounded,
`run-v2`): the model narrates faithful spoken text and a deterministic verifier checks
invariants, grounded in page images, gated on the corpus (functional spec, section 7). The
v1 `run` command is unchanged and remains available.

## Common commands

```
uv sync                                              # install deps into .venv
uv run pytest                                        # full offline test suite
uv run ruff check . && uv run ruff format --check .  # lint + format
uv run pyright                                       # strict type check
uv run audiobook run sample/Chapter6_preview.pdf --dry-run
```
