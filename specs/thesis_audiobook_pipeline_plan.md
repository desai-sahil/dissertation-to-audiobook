# Thesis-to-Audiobook Pipeline: Planning Spec

**Status:** planning phase, no implementation yet
**Purpose:** instructions for the agents that will build each stage
**Input:** a rendered PDF (universal lowest-common-denominator). Word and LaTeX sources are optional fast paths, see "Source-aware fast path" below.
**Output:** a navigable audiobook (M4B with chapter markers, or per-chapter MP3) generated via ElevenLabs.

---

## 0. Design principles (read first)

1. **Never go PDF to text to TTS directly.** Go PDF to a structured document model (the IR), then to a reviewable spoken script, then to audio. Each transformation is a pass over the IR. The IR is the contract between agents.
2. **Two review gates.** Gate A (optional) after structure extraction, for messy PDFs. Gate B (mandatory) is the spoken script, reviewed and editable *before* any TTS spend. TTS at thesis scale costs real money and is the last place you want to discover a mispronunciation.
3. **The lexicon is a first-class, reusable artifact.** Domain pronunciations and expansions (gs, psi_xyl, slac1) live in a versioned file, not hard-coded. It is reused across every thesis in the same field.
4. **Configurable by listener.** A committee member wants more rigor (some equations, citations). A family listener wants almost none. One profile flag drives equation verbosity, citation policy, and table handling.
5. **Idempotent and cached.** Cache TTS per chunk keyed by a hash of (text, voice, model, settings, dictionary version). A small script edit should re-render only the changed chunks, not the whole thesis.
6. **Keep provenance.** Every spoken chunk carries a back-pointer to its source location (chapter, page, block id). This enables debugging, and later a read-along feature.

---

## 1. The intermediate representation (IR)

A single JSON document that every stage reads and writes. Sketch:

```json
{
  "meta": {"title": "...", "author": "...", "degree_date": "...", "profile": "committee"},
  "blocks": [
    {
      "id": "ch1.p3",
      "type": "paragraph|heading|figure_caption|table|equation_display|equation_inline|footnote|reference_list|frontmatter|backmatter|code",
      "chapter": 1, "section": "1.2", "page": 14,
      "text": "...raw text...",
      "spoken": null,
      "keep": true,
      "handling": "speak|skip|gloss|summarize|announce",
      "refs": ["bib:smith2019"],
      "latex": "...for equations...",
      "notes": "judgment calls flagged here"
    }
  ],
  "figures":  {"fig3": {"caption": "...", "ref_points": ["ch2.p7"]}},
  "equations":{"eq4": {"latex": "...", "gloss": null}},
  "tables":   {"tab1": {"raw": "...", "summary": null}},
  "citations":{"[12]": {"bib_key": "jain2025", "spoken": "Jain and colleagues, 2025"}},
  "bibliography": {"jain2025": {"authors": [...], "year": 2025, "title": "..."}}
}
```

`text` is the source. `spoken` is filled in by later stages. Stages never overwrite `text`; they only populate `spoken`, `handling`, `keep`. This keeps every transformation auditable.

---

## 2. Stage-by-stage agent briefs

### Agent 1 — Ingest and Parse
**Goal:** PDF to structured markdown plus registries.
**Do:**
- Run **Marker** as the primary parser (best all-round structure and math fidelity, fast, local). Use **MinerU** instead when the thesis is equation-heavy and Marker's math output is weak (MinerU has the strongest LaTeX formula recovery).
- Run **GROBID** in parallel, purely to get (a) the bibliography parsed into structured entries and (b) inline citation markers linked to those entries. This is the only tool that reliably does the citation-to-bibliography linkage that the reference-verbalizing stage depends on.
- Emit: structured markdown, a figure registry (caption + bounding box + page), an equation registry (LaTeX where available, else a page-region image for later OCR), a table registry, and the GROBID citation map and reference list.
**Watch for:** all parsers mis-detect heading levels and reading order on complex layouts. Flag low-confidence pages for Gate A review rather than silently guessing.
**Acceptance:** chapters and sections recovered in correct order; bibliography parsed; at least 90 percent of inline citations linked.

### Agent 2 — Document Model Builder
**Goal:** merge parser outputs into the canonical IR and clean PDF artifacts.
**Do:**
- De-hyphenate words split across line breaks (photosyn- \n thesis to photosynthesis).
- Normalize ligatures (fi, fl) and unicode quirks.
- Repair reading order; strip running headers, footers, page numbers, line numbers.
- Tag every block with a `type`. Attach each figure caption to its figure; attach footnotes to their anchor.
- Merge the GROBID citation map into the `citations` table.
- Identify and tag front matter (title page, TOC, list of figures, list of tables, abstract) and back matter (appendices, SI, bibliography).
**Acceptance:** clean IR with typed blocks, no hyphenation artifacts, captions and footnotes correctly associated.

### Agent 3 — Content Selection and Filtering
**Goal:** decide what gets spoken, driven by the profile.
**Default rules:**
- **Skip entirely:** TOC, list of figures, list of tables, page numbers, the raw bibliography block (citations are voiced inline instead).
- **Keep, configurable:** abstract (keep), acknowledgments (keep, nice for family and committee), appendices and SI (skip by default, toggle on).
- **Special handling:** equations to Agent 4, tables to Agent 5, captions to Agent 5, citations to Agent 6.
**Profiles:**
- `committee`: equations glossed not skipped, citations brief, tables summarized.
- `general`: equations mostly skipped with a pointer, citations dropped or first-author-only, tables skipped with a one-line note.
**Acceptance:** every block has `keep` and `handling` set.

### Agent 4 — Math and Notation Transformer
**Goal:** make math listenable without belaboring it. Three tiers, chosen by profile.
- **Inline symbols and variables (always voiced):** map via the lexicon. gs to "stomatal conductance", psi_xyl to "xylem water potential", R^2 to "R squared", A_n to "net assimilation rate". Greek letters to names where no domain expansion exists (psi to "psi", mu to "mu").
- **Display equations (the 3-compartment hydraulic ODEs, MCMC likelihoods):**
  - `general`: announce and point. "Equation 4 expresses total conductance as a function of the soil, xylem, and outer-xylem compartments." Do not read the equation.
  - `committee`: LLM-generated one-sentence gloss from the equation's LaTeX. Feed LaTeX to the model, ask for a single spoken sentence capturing what the equation says, not how it is typeset.
  - `full` (rare, opt-in): convert to spoken math with an accessibility engine (MathCAT or the MathJax Speech Rule Engine) from MathML or LaTeX. Use sparingly; literal display-equation reading is fatiguing.
- **Simple inline equations (A = gs * D):** voice as "A equals gs times D" or skip per profile.
**Note:** when only a rendered image of an equation exists (no LaTeX), OCR it first (Nougat, or an LLM vision pass) to recover LaTeX before glossing.
**Acceptance:** no display equation is read verbatim under default profiles; every inline symbol resolves through the lexicon.

### Agent 5 — Figure, Table, and Caption Verbalizer
**Goal:** clean captions for the ear, and decide where they are spoken.
**Captions:**
- Expand "Fig. 3" to "Figure 3", panel labels "(A)" to "Panel A".
- Normalize stats and units inside captions (see Agent 6 rules): "n=6" to "n equals six", "*p<0.05" to "asterisk, p less than zero point zero five", "umol m^-2 s^-1" to "micromoles per meter squared per second".
- **Placement decision:** read the caption at the first in-text reference point ("as shown in Figure 3"), not at the figure's physical location in the PDF (which lands mid-paragraph in reading order). Fall back to end-of-section if no reference is found.
**Tables:** cannot be read cell by cell. Default: LLM produces a single spoken sentence summarizing the table ("Table 1 reports gas-exchange parameters for wild type and the GhSLAC1 knockout across four water potentials"). `general` profile: skip with a one-line note.
**Acceptance:** captions are fluent when read aloud; no raw table grids reach the script.

### Agent 6 — Text Normalizer for TTS (the heavy stage)
**Goal:** turn clean text into speakable text. This is mostly a deterministic rules engine plus the lexicon. Categories:
- **Numbers and stats:** "37%" to "thirty-seven percent"; "p<0.05" to "p less than zero point zero five"; "5.2 +/- 0.3" to "five point two, plus or minus, zero point three"; "10^-3" to "ten to the minus three"; "2-8" (en dash range) to "two to eight"; "R-hat from 2-8" handled as a range.
- **Units:** "umol m^-2 s^-1", "CO2" to "C O two", "H2O" to "water" (or "H two O" per lexicon), "kPa", "MPa".
- **Acronyms:** lexicon decides spell-out-as-letters vs expand. "WT" to "wild type", "MCMC" to "M C M C", "FDR" to "false discovery rate", "ODE" to "O D E", "ABA" to "A B A".
- **Gene and mutant names:** these read terribly by default. Lexicon entries for slac1, ost1-3, aao3-2, GhSLAC1 with chosen spoken forms (gene nomenclature is usually spoken as letters plus number, confirm your lab's convention).
- **Cross-references:** "see Section 3.2" to "see section three point two", "as in Chapter 1" voiced naturally.
- **Sentence segmentation:** use a segmenter that knows scientific abbreviations (et al., e.g., i.e., Fig., vs., approx., cf.) so they do not trigger false sentence breaks and bad TTS pauses.
**Key architecture choice:** prefer doing expansions in the **ElevenLabs pronunciation dictionary** (alias rules) rather than rewriting the script text, so the human-readable script at Gate B stays readable ("gs" stays "gs" on the page, but speaks as "stomatal conductance"). Use script-level rewriting only for things a reviewer needs to see expanded (numbers, stats).
**Acceptance:** script contains no raw notation that a voice would mangle; the lexicon covers all recurring domain terms.

### Agent 7 — Script Assembler
**Goal:** produce the reviewable spoken script and the chunk plan.
**Do:**
- Insert structural announcements: "Chapter 1. A review of stomatal conductance models." "Section 2.3, Results."
- Insert intro (title, author, "an audiobook rendering of the doctoral dissertation of...") and a short outro.
- Insert pauses. Use `<break time="x.xs"/>` tags after headings and between sections, sparingly (too many break tags cause audio instability on ElevenLabs). Note: `multilingual_v2` honors break tags; `v3` does not, use sentence-final periods for pacing there.
- Emit two artifacts: the **human-readable script** (markdown, for Gate B) and the **chunk plan** (ordered list of chunks with text, chapter, ids, neighbor pointers).
**Gate B happens here.** The user proofreads and edits the script. Edits flow back into the IR and only changed chunks lose their cache entry.

### Agent 8 — Lexicon and Pronunciation Manager
**Goal:** maintain and publish the domain lexicon.
**Lexicon entry schema:**
```json
{"grapheme": "gs", "type": "alias", "alias": "stomatal conductance",
 "case_sensitive": true, "word_boundaries": true, "scope": "plant-physiology"}
{"grapheme": "psi", "type": "phoneme", "phoneme": "saɪ", "alphabet": "ipa", "model": "flash_v2"}
```
**Do:** push the lexicon to an ElevenLabs pronunciation dictionary via the `add-from-rules` endpoint; store the returned dictionary id and version id; pass those as `pronunciation_dictionary_locators` on every TTS request.
**Model caveat:** alias rules work on all models including `multilingual_v2`. Phoneme/IPA rules only apply on `flash_v2` and `v3`. Most of your needs (gs, psi_xyl, gene names) are alias rules, so `multilingual_v2` is fine. Reserve phoneme rules for the handful of Greek letters where the alias spelling still misreads.

### Agent 9 — TTS Renderer
**Goal:** chunk text to audio, with continuity and caching.
**Do:**
- Chunk at sentence or paragraph boundaries, staying under the per-request limit (5,000 chars paid; keep chunks to roughly 1,500-2,500 chars for stability and cheap re-rendering).
- Model: `eleven_multilingual_v2` for the final deliverable (highest narration quality). Use `flash_v2_5` for cheap previews. Consider `v3` only if you want expressive delivery and can tolerate lower pronunciation consistency and no SSML breaks.
- For prosody continuity across chunks, pass `previous_text` and `next_text` (or `previous_request_ids` / `next_request_ids`, max 3) so chunk boundaries do not sound clipped.
- Set `seed` for reproducibility. Decide `apply_text_normalization`: since Agent 6 already normalized, consider `off` to avoid double handling, but test, ElevenLabs normalization is decent and `auto` may be safer for stray cases.
- Attach the pronunciation dictionary locators.
- **Cache** each chunk's audio by hash(text, voice, model, settings, dict_version). Skip unchanged chunks on re-render.
- Retry on failures; ElevenLabs allows up to 2 free regenerations for identical content.
**Cost control:** before a full render, estimate characters (a thesis is roughly 50,000-100,000 words, about 300,000-600,000 characters) and surface the cost using current per-character pricing (check the pricing page, it shifts). Always render a single preview chapter first.
**Alternative MVP path:** ElevenLabs **Studio** (formerly Projects) handles long-form chunking and stitching for you (up to 200 chapters, 400 paragraphs each). It is faster to stand up but gives less programmatic control over per-chunk normalization and caching. Trade-off flagged for decision below.

### Agent 10 — Audio Assembler
**Goal:** assemble chunks into the deliverable.
**Do:**
- Concatenate chunk MP3s per chapter (ffmpeg).
- Build an **M4B** with chapter markers (ffmpeg plus a chapter metadata file, or AtomicParsley) so the audiobook is navigable. Alternatively emit per-chapter MP3s.
- Embed metadata: title, author, narrator (voice name), year.
- Keep the provenance map (audio timestamp to source block) as a sidecar for debugging and future read-along.
**Acceptance:** a single navigable audiobook file plus per-chapter files, with correct chapter titles and metadata.

---

## 3. Source-aware fast path

PDF is the universal input and the reach play, but it is the hardest. When the original **LaTeX or Word** source is available, prefer it: structure and real math source are already present, so Agents 1 and 2 mostly collapse. Your existing `thesis_audio` LaTeX-to-MP3 work becomes the fast path; the PDF pipeline is the general fallback. Detect input type at ingest and route accordingly.

---

## 4. Cross-cutting concerns

- **Profiles / config:** one config object (`profile`, equation tier, citation policy, table handling, include_appendices, voice_id, model_id). Drives Agents 3-7 and 9.
- **Caching:** chunk-level, as above. The single biggest cost saver across edit-render cycles.
- **Cost estimator and preview mode:** mandatory before full render.
- **QA pass:** spot-listen the first and last chunk of each chapter and any chunk flagged low-confidence at parse time.
- **Provenance:** retain throughout for debugging and read-along.

---

## 5. Open decisions for you (judgment calls flagged, not silently made)

1. **Default target listener:** `committee` or `general`? This sets the defaults for equations, citations, and tables. My lean: ship `committee` as default since your committee members are the real first users, with a one-flag switch to `general`.
2. **Citation policy default:** drop, brief (first author + year), or full? My lean: `brief`, since dense citation lists read terribly in full and dropping loses attribution your committee will notice.
3. **Equation default tier:** announce-and-point vs LLM-gloss. My lean: gloss for `committee`, announce for `general`.
4. **Output container:** M4B with chapter navigation, or flat per-chapter MP3? My lean: M4B, it is what makes this an audiobook rather than a long voice memo.
5. **Voice model:** `multilingual_v2` (quality, recommended for the deliverable) vs `flash_v2_5` (cheap previews) vs `v3` (expressive, less consistent, no SSML breaks). My lean: `multilingual_v2` final, `flash_v2_5` preview.
6. **Build path:** own chunked-TTS pipeline (full control, caching, custom normalization, more code) vs ElevenLabs Studio long-form API (faster MVP, less control). My lean: own pipeline given your caching and determinism goals, but Studio is the faster way to a first listenable draft.
7. **Read-along feature:** keep the provenance source-map now to enable a future synchronized-text view, even if you do not build the viewer yet? Low cost to retain, high cost to reconstruct later.

---

## 6. What was easy to miss (added beyond the original brief)

- The reviewable spoken script as a proofread-before-you-pay gate.
- Tables (the original brief covered figures, equations, references, but not tables).
- Footnotes, endnotes, front matter, back matter, and appendices/SI policy.
- Cost control, preview mode, and chunk-level caching at thesis scale.
- Chapter navigation (M4B) vs a flat audio file.
- Cross-references ("see Section 3.2") voiced naturally.
- Units and statistics notation as a distinct normalization category from equations.
- Gene and mutant name pronunciation (slac1, ost1-3, aao3-2).
- PDF extraction artifacts: de-hyphenation, ligatures, reading order, headers/footers.
- Using the ElevenLabs pronunciation dictionary as the production mechanism (so the script stays readable) rather than rewriting text in place.
- Sentence-segmentation pitfalls from scientific abbreviations.
