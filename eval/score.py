"""Pure, deterministic scorers for the eval harness. No I/O.

Given a produced spoken SCRIPT (str), a STRUCTURE result (how many chapters the pipeline found),
and the committed LABELS for a thesis, these return per-dimension scores. Everything is a function
of (output, labels), so the same scorers grade any architecture - they never look at how the
script was produced.

Dimensions:
  - structure: chapters the pipeline detected vs the thesis's real chapter count (recall).
  - citation/markup strip: labeled leak fingerprints (any form: "span id", a DOI, a page anchor)
    that MUST be absent from the spoken script.
  - value preservation: labeled values/terms that MUST survive into the spoken script.
  - raw-notation leak: forbidden raw characters that should never reach a narrator
    (reuses normalization.FORBIDDEN_RAW_TOKENS - label-free).

A label/pattern may be a plain substring (whitespace- and case-insensitive) or a regex with an
"re:" prefix (so a page-anchor leak like "page eleven to zero" can be matched across its varying
spelled-out numbers).
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import StrictModel
from thesis_audiobook.normalization import FORBIDDEN_RAW_TOKENS
from thesis_audiobook.verifier import verify_segment


class Labels(StrictModel):
    """The committed ground truth for one thesis (eval/corpus/<id>/labels.json)."""

    thesis_id: str
    title: str = ""
    fields: list[str] = []
    # The thesis's real chapter titles (count = len); structure recall is detected/len.
    expected_chapters: list[str] = []
    # Leak fingerprints (plain substring, or "re:<regex>") that MUST be absent from the spoken text.
    must_be_absent: list[str] = []
    # Values/terms (plain or "re:<regex>") that MUST survive into the spoken script.
    must_be_present: list[str] = []
    notes: str = ""


class StructureResult(StrictModel):
    """What the pipeline actually inferred for a thesis (eval/corpus/<id>/result.json)."""

    chapters_detected: int = 0
    backmatter_skipped_blocks: int = 0


class DimensionScore(StrictModel):
    dimension: str
    passed: int
    total: int
    rate: float
    misses: list[str] = []  # the specific items that failed, for the report

    @classmethod
    def of(
        cls, dimension: str, passed: int, total: int, misses: list[str] | None = None
    ) -> DimensionScore:
        rate = 1.0 if total == 0 else round(passed / total, 3)
        return cls(dimension=dimension, passed=passed, total=total, rate=rate, misses=misses or [])


class ThesisScore(StrictModel):
    thesis_id: str
    dimensions: list[DimensionScore] = []


# SSML control tags the assembler legitimately emits for TTS pacing/voicing. They are speech
# directives, not narrated content, so the scorers strip them first. Any OTHER angle-bracket markup
# (e.g. a leaked <span>/<sup> from extraction) is left in place so it still trips the leak check.
_SSML_CONTROL = re.compile(
    r"</?(?:break|emphasis|prosody|say-as|phoneme|sub|voice|p|s)\b[^>]*>", re.IGNORECASE
)


def _speech_text(script: str) -> str:
    """The text a narrator actually voices: the script with SSML control tags removed."""
    return _SSML_CONTROL.sub(" ", script)


def _norm(text: str) -> str:
    return " ".join(_speech_text(text).split()).lower()


def _present(pattern: str, body_norm: str) -> bool:
    """Is `pattern` present in the whitespace/case-normalized body? `pattern` is a plain substring
    or, with an "re:" prefix, a regex (matched case-insensitively over the normalized body)."""
    if pattern.startswith("re:"):
        return re.search(pattern[3:], body_norm, re.IGNORECASE) is not None
    return _norm(pattern) in body_norm


def score_structure(result: StructureResult, labels: Labels) -> DimensionScore:
    """Chapters detected vs the real chapter count, scored as F1 so BOTH misses and over-detection
    cost. Recall-only (the old behavior) scored 1.0 for detecting 8 chapters where 6 exist, hiding
    that two were really references/appendix; F1 folds in precision. passed/total stays the recall
    view (matched/expected); rate is the F1."""
    expected = len(labels.expected_chapters)
    detected = result.chapters_detected
    matched = min(detected, expected)
    if expected == 0:
        rate = 1.0 if detected == 0 else 0.0
    else:
        recall = matched / expected
        precision = matched / detected if detected else 0.0
        denom = precision + recall
        rate = 0.0 if denom == 0 else round(2 * precision * recall / denom, 3)
    misses: list[str] = []
    if detected < expected:
        misses.append(f"detected {detected}/{expected} (missed {expected - detected})")
    elif detected > expected:
        misses.append(f"detected {detected} > {expected} expected ({detected - expected} extra)")
    return DimensionScore(
        dimension="structure (chapters)", passed=matched, total=expected, rate=rate, misses=misses
    )


def score_citation_strip(script: str, labels: Labels) -> DimensionScore:
    """Labeled leak fingerprints that must be ABSENT from the spoken script (higher = cleaner)."""
    body = _norm(script)
    leaked = [m for m in labels.must_be_absent if _present(m, body)]
    passed = len(labels.must_be_absent) - len(leaked)
    return DimensionScore.of("citation/markup strip", passed, len(labels.must_be_absent), leaked)


def score_value_preservation(script: str, labels: Labels) -> DimensionScore:
    """Labeled values/terms that must be PRESENT in the spoken script (higher = more faithful)."""
    body = _norm(script)
    missing = [v for v in labels.must_be_present if not _present(v, body)]
    passed = len(labels.must_be_present) - len(missing)
    return DimensionScore.of("value preservation", passed, len(labels.must_be_present), missing)


def score_raw_token_leak(script: str) -> DimensionScore:
    """Forbidden raw characters that must never reach a narrator (label-free). passed/total is a
    binary cleanliness flag; the misses list carries the leaked characters and how many. SSML
    control tags are stripped first - they are speech directives, not narrated symbols."""
    counts: dict[str, int] = {}
    for ch in _speech_text(script):
        if ch in FORBIDDEN_RAW_TOKENS:
            counts[ch] = counts.get(ch, 0) + 1
    misses = [f"{ch!r}x{n}" for ch, n in sorted(counts.items())]
    return DimensionScore.of("raw-token leak (clean=1)", 0 if counts else 1, 1, misses)


def score_faithfulness(pairs: list[tuple[str, str]]) -> DimensionScore:
    """Run the verifier over (source, spoken) segment pairs; rate = fraction with no violation.

    This is the dimension v2 introduces and v1 cannot report: v1 has no aligned source/spoken pairs
    (the deterministic transform never exposed them). The v2 generator emits the pairs, and this
    quantifies the residual drift the model's rewrite introduces, segment by segment."""
    clean = 0
    misses: list[str] = []
    for source, spoken in pairs:
        verdict = verify_segment(source, spoken)
        if verdict.ok:
            clean += 1
        elif len(misses) < 8:
            kinds = ",".join(sorted({v.kind for v in verdict.violations}))
            misses.append(f"[{kinds}] {spoken[:48]}")
    return DimensionScore.of("faithfulness (verifier)", clean, len(pairs), misses)


def score_thesis(script: str, result: StructureResult, labels: Labels) -> ThesisScore:
    return ThesisScore(
        thesis_id=labels.thesis_id,
        dimensions=[
            score_structure(result, labels),
            score_citation_strip(script, labels),
            score_value_preservation(script, labels),
            score_raw_token_leak(script),
        ],
    )


def render_scorecard(scores: list[ThesisScore]) -> str:
    """A markdown scorecard: one row per (thesis, dimension), with a per-dimension miss list."""
    lines = [
        "# Eval scorecard",
        "",
        "Per-dimension scores (rate 1.0 = perfect); misses list the specific failures.",
        "This is the v1 baseline the v2 rebuild must beat, not regress.",
        "",
        "| thesis | dimension | passed/total | rate | misses |",
        "|---|---|---|---|---|",
    ]
    for ts in scores:
        for d in ts.dimensions:
            miss = ", ".join(d.misses)[:80].replace("|", "\\|").replace("\n", " ")
            cells = f"{ts.thesis_id} | {d.dimension} | {d.passed}/{d.total} | {d.rate} | {miss}"
            lines.append(f"| {cells} |")
    return "\n".join(lines) + "\n"
