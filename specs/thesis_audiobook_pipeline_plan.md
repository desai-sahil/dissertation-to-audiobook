# Thesis-to-Audiobook Pipeline: Functional Spec

**Status:** built and validated end to end on full theses (Jain ~360pp, Gao). This is the
functional spec (what each stage does); [thesis_audiobook_build_spec.md](thesis_audiobook_build_spec.md)
is the engineering spec (how it is built and tested). When they disagree: this doc wins on behavior.
**Input:** a PDF, ingested via Marker/MinerU markdown (recommended) or an offline poppler fallback.
**Output:** a navigable audiobook (chaptered M4B/MP4 plus a whole-book MP3) via ElevenLabs.

---

## 0. Design principles

1. **Never go PDF to text to TTS directly.** Go PDF -> a structured document model (the IR) -> a
   reviewable spoken script -> audio. Each transformation is a pass over the IR; the IR is the
   contract between stages.
2. **Two review gates.** Gate A: structure warnings + the `out/<slug>.structure.md` map after
   parsing/cartography. Gate B (the important one): the reviewable spoken script + the
   `out/<slug>.ledger.md` of every judgment, vetted *before* any TTS spend. TTS at thesis scale
   costs real money; it is the last place to discover a mistake.
3. **Claim-safety over cleverness.** The LLM never writes narration from scratch. It emits labels,
   enums, or `find -> replace` edits; deterministic code renders; deterministic guards validate
   risky edits. The author's data and claims (numbers, signs, units, findings) are never altered -
   only how *notation* is voiced, and (in copy-edit mode) the author's mechanical errors, are fixed.
4. **Lean on the model + a ledger, not a per-thesis regex treadmill.** Per-thesis variability
   (which regions exist, novel pronunciations, source typos, extraction artifacts) is handled by the
   LLM stages under guards and logged to the ledger. General bugs that hold across theses are fixed
   once, deterministically.
5. **Configurable by listener.** A `committee` profile keeps more (summarized tables); a `general`
   profile keeps less (tables skipped). Both announce equations by number and discard citation
   machinery.
6. **Idempotent and cached.** TTS is cached per chunk; each LLM stage is cached by a versioned
   content key. A small edit re-renders only the changed chunk and its seams.
7. **Keep provenance.** The IR `text` field is never overwritten; every chunk back-points to its
   source blocks; `out/<slug>.provenance.json` maps audio timestamps to block ids.

---

## 1. The intermediate representation (IR)

A single typed document every stage reads and writes (see the build spec for the models). Sketch:

```json
{
  "meta": {"title": "...", "author": "...", "degree_date": "...", "profile": "committee"},
  "blocks": [
    {"id": "m12", "type": "paragraph|heading|figure_caption|table|equation_display|equation_inline|footnote|reference_list|frontmatter|backmatter|code",
     "chapter": 1, "section": "1.2", "page": 14, "text": "...source...", "spoken": null,
     "keep": true, "handling": "speak|skip|summarize|announce", "refs": [], "latex": "...", "notes": []}
  ],
  "figures": {"...": {...}}, "equations": {"...": {...}}, "tables": {"...": {...}},
  "script": "...assembled spoken script...",
  "chunks": [{"id": "c1", "text": "...", "chapter": 1, "block_ids": ["m12"], "prev_id": null, "next_id": "c2"}]
}
```

`text` is the source and is never overwritten; `spoken` is filled by later stages; `script`/`chunks`
are derived by the assembler. There is no `citations`/`bibliography` map (citations are discarded).
The cartographer's `StructureMap` (claim-safe regions) is held on the Context, rendered to
`structure.md`, and applied to block types deterministically.

---

## 2. Pre-pipeline: ingest + extraction repair (phases 1-2)

Run once per thesis to produce a clean markdown the pipeline ingests.

**Marker (or MinerU), run standalone.** Marker gives the best structure + math fidelity; it is kept
out of this project's venv (pin conflicts) and run as an isolated tool, producing markdown that the
pipeline reads via `--markdown`. Poppler (`pdftotext`) is the in-repo offline fallback for quick
tests; it mangles dense notation, so Marker is preferred for the deliverable.

**Extraction repair (`repair-extraction`), two-pass and guarded.** Pass 1: the model proposes two
kinds of edit on the raw markdown - `noise` (typographic/OCR: detached accents, stray spacing,
case-preserving) and `artifact` (de-shred Marker-mangled notation: a decimal split into per-character
`<sup>` tags, a Miller index written as `< <sup>111</sup> >`, glued scientific notation). Code
applies only edits that pass a guard: `noise` must preserve the exact word-token sequence and case;
`artifact` must restore the value using ONLY the digits/symbols already present (ordered digits
identical, no value symbol dropped or invented, no new letter) - so it may re-render `<sup>0</sup>.1`
-> `0.1` but can never turn `0.15` into `0.5`. Pass 2 re-reads the cleaned markdown and flags
residual defects. Output: `*.cleaned.md` + a `*.repair-report.md`. `check-extraction` is the
read-only audit alone.

---

## 3. The pipeline stages (phase 3 onward)

Order: ingest -> build_ir -> structurer -> cartographer -> select -> curate -> math -> figures ->
citations -> normalize -> appendix_signpost -> assemble_script -> script_repair -> script_qc ->
lexicon -> tts -> assemble_audio. The first LLM stages (structurer, cartographer, curate) run on the
clean markdown; each is a no-op offline (mock LLM).

**Ingest + build_ir (document model).** Parse the markdown into typed `Block`s; clean PDF artifacts
(de-hyphenate line breaks, normalize ligatures/mojibake, reflow across page breaks, strip running
headers/footers/page numbers, attach captions/footnotes), tag a `BlockType`, and tag front/back
matter. Low-confidence structure -> `WarningsSink` (Gate A), never a silent guess.

**Structurer (LLM block-kind classifier).** Corrects each block's *kind* (prose / heading /
equation / code / figure / table / reference / frontmatter) so non-narratable material (a source-code
appendix, fenced or spaced-out) is typed `code` and skipped whatever the formatting. Claim-safe
(returns only a kind per block id), cached one call/doc, every change logged to
`structure-changes.md`. `--no-structurer` disables it.

**Cartographer (LLM structure map).** Reads a compact outline once and returns `Region`s: which
spans are chapters/body (include) vs table of contents, lists, per-chapter and main bibliographies,
and appendices (skip). It emits only enums + EXISTING block-id spans + a verbatim label (shown only
in `structure.md`), so it cannot inject audio. Corrected types flow into `select`. Rescues theses
whose heading scheme `build_ir` cannot detect alone. `--no-structure-eval` disables it.

**Select (content selection, deterministic, profile-driven).** Sets `keep`/`handling` per block.
Skip: TOC, lists of figures/tables, page numbers, bibliographies, code, appendices (default).
Keep: body, abstract, biographical sketch, acknowledgements, dedication. Special handling: equations
-> announce, tables -> summarize/skip, captions -> skip.

**Curate (LLM pronunciation manager).** Returns a pronunciation plan: acronyms (expand on first use,
then a spelled short form), domain terms (phonetic reads), flattened-notation reads, and
de-hyphenations. It changes only *how* terms are said, never the prose. Single-letter and bare
Greek-letter keys are ignored (they collide with initials, the article "A", and overloaded
symbols). Cached one call/doc; written to `qa.md`. `--no-curate` disables it.

**Math (announce, not gloss).** Display equations are announced by their real number ("Equation two
point three"); unnumbered intermediate steps are dropped. There is no LLM gloss - an earlier gloss
tier was removed because it hallucinated. Inline symbols/variables are voiced via the lexicon and
the normalizer.

**Figures + tables.** Figure/table captions are skipped (heavily visual). Tables: `committee`
summarizes via one LLM sentence; `general` skips with a note.

**Citations (machinery to discard, NotebookLM-style).** Deterministically strip reference markers -
bracketed `[12]`, superscript numbers, period/comma-fused `word.41` / `group,20, 21`, parenthetical
`(Geiger et al., 2009)`, `et al.,N`. Narrative author mentions ("Chalmer et al. note that...") are
genericized to one phrase from a FIXED plural set ("researchers note that...") via a cached LLM call
that maps each mention to a phrase (claim-safe; offline degrades to "and others"). No bibliography is
parsed or read.

**Normalize (the heavy deterministic rules engine).** Turn clean text into speakable text: numbers
and stats ("37%" -> "thirty-seven percent", "p<0.05", "5.2 +/- 0.3", ranges, decades, scientific
notation, NxM dimensions -> "times"), units (full spoken words), acronyms, Greek, cross-references
("Section 2.3" -> "section two point three"), LaTeX/markup flattening, mojibake, repetition cleanup,
and sentence segmentation that knows scientific abbreviations. Runs to a fixed point (idempotent) and
guarantees the no-leak invariant (no raw notation survives). Glosses/summaries are re-normalized too.

**Appendix signpost.** When appendices are skipped, the first in-text "Appendix X" reference per
chapter gets one fixed spoken aside ("...referenced in the appendix, not included here..."); the
rest pass through. Deterministic detection + fixed template = claim-safe.

**Assemble script (Gate B).** Insert structural announcements ("Chapter 1. ..."), an intro/outro,
and sparing pauses, then emit the reviewable `script.md` and the `chunks.json` plan (ordered chunks
with neighbor pointers). This is the proofread-before-you-pay artifact.

**Script repair (the writer + copy-edit).** A bounded loop (up to 3 rounds) where a writer proposes
small `find -> replace` edits, applied whole-token, re-reading until a round changes nothing. In the
default **copy-edit** mode it fixes how notation is voiced AND the author's clear mechanical errors
(spelling typos, fused words, meaning-preserving grammar/readability) and pure-text extraction
artifacts - each tagged by kind, each cleared by the deterministic `copyedit_guard` (values, polarity
words, and directional result words preserved; at most one content-word substitution; the author's
data/claims never changed - a suspected number/sign error is flagged, not edited). `--as-written`
restores strict notation-only. Every applied/rejected edit is logged to the ledger.

**Script QC (the pre-TTS gate, bounded loop).** An Opus sweep audits the finished script for
pipeline defects (leaked markup, garble, truncation, a number voiced wrong, a reference left
unread); if any, one Sonnet fix pass turns them into guarded edits; a single Opus confirm re-audits.
Flags whose location is not a verbatim substring are dropped (honesty filter). HIGH-severity flags
block a billed render (override with `--force`). `--no-qc-loop` keeps only the read-only audit.

**Lexicon + TTS + assemble_audio (phase 5).** Publish the pronunciation dictionary; render chunks
(content-addressed cached, neighbor `previous_text`/`next_text` for prosody, `eleven_multilingual_v2`
for the deliverable, flash for previews); concat + chapterize via ffmpeg into the chaptered file +
whole-book mp3, embed metadata + cover, and write the provenance sidecar.

---

## 4. Cross-cutting concerns

- **Profiles / config:** one `Config` + a TOML `Profile`; drives select, math, figures, tts.
- **Caching:** chunk-level TTS + per-stage versioned LLM caches; the biggest cost saver across
  edit-render cycles. Re-running unchanged markdown reuses LLM results with no billing.
- **Cost estimator + preview:** `--dry-run` (no calls) and `--preview` (first chapter) are mandatory
  before a full render.
- **The update ledger** (`ledger.md`): one reviewable record of every judgment - structure
  inferred, pronunciation plan, citation genericizations, author corrections / extraction artifacts /
  rejected-flagged edits. The accountability layer for leaning on the LLM.
- **Live status spinner:** a one-line stderr spinner shows the current stage / agent loop during a
  real run (isatty-gated; silent in pipes/CI; never changes output).
- **Provenance + QA:** retained throughout for debugging and a future read-along.

---

## 5. Resolved decisions (the original "open" calls, now settled)

1. **Default listener:** `committee` (the real first audience), one flag to `general`.
2. **Citations:** neither brief nor full - **discarded as machinery** and narrative mentions
   genericized (NotebookLM-style). No bibliography is read.
3. **Equations:** **announce by number**, never LLM-glossed (the gloss hallucinated). `full` exists
   but is opt-in.
4. **Author's text:** by default **copy-edited** for mechanical errors (typos/grammar/spacing) under
   a deterministic claim-safety guard; `--as-written` reads strictly verbatim. The author's data and
   claims are never auto-changed.
5. **Output container:** chaptered **M4B/MP4** plus a whole-book MP3.
6. **Voice model:** `eleven_multilingual_v2` for the deliverable, flash for previews.
7. **Build path:** own chunked-TTS pipeline (control, caching, determinism), not Studio.
8. **Read-along:** provenance source-map retained now to enable a future synchronized view.

---

## 6. What the original brief missed (now in the pipeline)

The reviewable script + ledger as a pay-gate; the structurer + cartographer for robust structure
across theses; the copy-edit stage + deterministic guards; the two-pass extraction repair with
artifact de-shredding; the bounded pre-TTS QC loop; tables, footnotes, front/back matter, appendix
signposting; cost control, preview, chunk-level caching; chapter navigation; cross-references; units
and statistics as a normalization category distinct from equations; gene/mutant and Greek
pronunciation; PDF extraction-artifact handling; and the markdown-ingestion path that lets Marker run
isolated.

---

## 7. The v2 engine (built): invert the split, ground in vision, gate on a corpus

Principle 4 above warned against a "per-thesis regex treadmill." Running real theses showed the
treadmill survives even with LLM labels, because it moved into the *renderer*: deterministic code
that turns labels into spoken text must enumerate an open set of surface forms (every citation shape,
every chapter-heading scheme, every notation glyph). Zhu broke exactly there - roman-numeral,
span-wrapped headings yielded zero detected chapters, and citation/markup leaked into the narration.

The v2 reframe (built and validated on the corpus; the `run-v2` command):

1. **Invert the labor split.** The model produces the *spoken text* (a constrained, faithful rewrite:
   expand units/numbers, drop citation markers of any form, announce equations by number, keep every
   value and claim); deterministic code *verifies invariants*. Invariants are universal so a verifier
   generalizes; surface forms are not so a renderer does not. The cleverness moves into the verifier,
   which becomes the most-tested component.
2. **Ground the hard parts in the page image.** Almost every extraction failure (sup-vs-exponent,
   dropped sigmas, page-anchor spans, inconsistently-leveled headings) is an artifact of trusting
   lossy extracted text. The rendered page is ground truth and the model reads it directly. Vision
   collapses the whole extraction-artifact failure class and hits structure, citations, equations,
   and figures at once.

**Tradeoff (explicit).** v1's claim-safety was *by construction* - deterministic code wrote the
output, so it could not alter a value or claim. v2's is *bounded error*: the verifier is a floor
(values preserved and in order, no invented number or claim, polarity/direction intact,
near-paraphrase not free composition, a speakable-character allowlist) but cannot catch a same-arity
semantic swap. Faithfulness therefore rests on the model + a vision QC judge + **the corpus**. That
is why the corpus + eval harness was built first (build spec, section 7.6): it is the only thing that
measures the residual drift v2 introduces, and the bar v2 must clear.

**The v2 pipeline (as built, `run-v2`).** PDF -> page images (poppler, ground truth) + light per-page
text as a block->page alignment aid only -> a vision structure pass (the cartographer, grounded:
labels section *kinds*, read vs skip) -> a verifier-gated narrator: the model writes the spoken text
for each read segment, the deterministic verifier checks invariants, and a failure re-narrates then
escalates to the **page image** (vision QC, with the page as ground truth) before the segment is held
-> non-prose is announced (equations by number) or skipped -> then assemble/lexicon/TTS/assembly are
reused wholesale from v1. The cover is **generated** from the title + author unless `--cover` is
given. A confidence gate (held-or-flagged rate) stops a billed render of confidently-broken audio
unless `--force`; `--preview` renders only the first chapter for a cheap end-to-end check. The TTS
cache key includes the backend (mock vs elevenlabs), so a mock render's silent audio is never served
to a real one. Validated across Gao, Zhu, and Jain (faithfulness ~0.96-0.995); a high held/flagged
rate routes a thesis to human review instead of shipping confidently-broken audio. The v1 `run`
command is unchanged and remains available.
