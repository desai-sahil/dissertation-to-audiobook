"""The verifier: v2's deterministic faithfulness floor over a (source, spoken) pair.

v1 was safe BY CONSTRUCTION - deterministic code wrote the output, so it could not change a value or
claim. v2 lets the model write the spoken text, so safety becomes BOUNDED ERROR and this verifier is
the floor. It cannot prove a rewrite faithful (a same-arity semantic swap like "inhibits" ->
"regulates" slips through; that is the vision QC judge's and the corpus's job). It catches the
mechanical ways a constrained rewrite goes wrong:

  1. SPEAKABLE  - the spoken text contains only narratable characters (an allowlist, the inverse of
                  normalization.FORBIDDEN_RAW_TOKENS), so leaked markup/notation or an unvoiced
                  digit trips it - it generalizes across fields, unlike a denylist of bad symbols.
  2. VALUES     - every measurement/statistic in the source survives into the spoken text, in order.
                  Scope is decimals and percentages (number_to_words is the spelling oracle); bare
                  integers are out of scope on purpose - they are dominated by citation years,
                  reference numbers, and page numbers that a faithful rewrite correctly drops.
  3. POLARITY   - negations exact (adding/dropping a "not" flips a claim) and scope words not
                  dropped, while voicing-driven additions ("<" -> "less") are allowed.
  4. DIRECTION  - net up/down preserved: a flip (up-only -> down-only) or total loss is flagged,
                  but synonyms (higher -> greater) and voiced additions ("-" -> "negative") pass.
  5. PARAPHRASE - the spoken text does not inject many content words absent from the source, which
                  catches free composition / a hallucinated clause (a constrained rewrite stays
                  close to the source wording).

The model only writes; this only checks. A violation routes the segment to regenerate, then escalate
to human review. Pure, no I/O. Intended to be the most-tested module in the package.
"""

from __future__ import annotations

import re
import string
from collections import Counter

# Reuse the copy-edit guard's content-word multiset (same package; intentional shared seed). The
# polarity/direction COUNTS are handled here, not via copyedit's exact-equality helpers: v2's spoken
# text voices symbols (< -> "less than", - / <0 -> "negative", > -> "greater"), which legitimately
# adds these words, so the verifier needs a relaxed, voicing-aware check copyedit must not have.
from thesis_audiobook.copyedit import content_words
from thesis_audiobook.ir import StrictModel
from thesis_audiobook.normalization.numbers import number_to_words

# Word classes for the relaxed claim checks (see _verify_counts):
#  - NEGATIONS: exact count (adding OR dropping a "not" flips meaning; voicing rarely adds them).
#  - SCOPE: no-drop (don't lose "only"/"all"; voicing a "<" legitimately ADDS "less").
#  - UP / DOWN: net direction; a true flip (up-only -> down-only) or total loss is the violation,
#    while synonyms (higher -> greater) and voiced additions ("negative" for a "-") pass.
_NEGATIONS = frozenset(
    {"not", "no", "never", "none", "neither", "nor", "cannot", "without", "nothing", "nobody",
     "hardly", "scarcely", "barely", "non"}
)  # fmt: skip
_SCOPE = frozenset(
    {"only", "all", "every", "each", "both", "more", "less", "fewer", "most", "least", "any",
     "some", "few", "many", "much"}
)  # fmt: skip
# above/below/under/over are deliberately EXCLUDED: they are usually positional ("as below", "see
# above", "the term under") rather than a directional finding, and caused false positives.
_UP = frozenset(
    {"increased", "increase", "increases", "increasing", "rose", "rise", "rises", "risen",
     "higher", "highest", "greater", "greatest", "positive", "positively", "faster",
     "doubled", "tripled", "quadrupled", "exceeded", "exceed", "gained", "gain", "upregulated"}
)  # fmt: skip
_DOWN = frozenset(
    {"decreased", "decrease", "decreases", "decreasing", "fell", "fall", "falls", "fallen",
     "lower", "lowest", "lesser", "negative", "negatively", "slower", "halved",
     "lost", "loss", "downregulated"}
)  # fmt: skip
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
_NEG_CONTRACTION = re.compile(r"[a-z]+n't")

VERIFIER_VERSION = "verifier-v1"

# Paraphrase tunables: flag only when the spoken text introduces BOTH an absolute and a relative
# excess of content words not present in the source (so ordinary synonym/voicing variation passes).
PARAPHRASE_MIN_NEW_TYPES = 5
PARAPHRASE_MAX_NEW_RATIO = 0.6

# Characters a narrator can speak: letters, whitespace, and ordinary sentence punctuation. Digits
# are deliberately EXCLUDED - by this stage every number should be spelled out, so a residual digit
# is an unvoiced number. Anything else (%, +/-, ^, <, >, [, ], a leaked LaTeX backslash, a bare "/"
# that should read "over", a stray Greek glyph) is non-speakable and trips the check.
_SPEAKABLE: frozenset[str] = frozenset(
    set(string.ascii_letters)
    | set(" \t\n")
    | set(".,;:!?'\"()-")
    | {"–", "—", "‘", "’", "“", "”", "…"}  # en/em dash, smart quotes, ellipsis (all speakable)
)

# Value tokens whose change would alter a claim: decimals (measurements, ratios, p-values) and
# integers written as a percentage. Bare integers are intentionally out of scope (see module docs).
# The (?<![\w.]) lookbehind means a leading "-" only counts as a sign when it is NOT preceded by a
# digit/word/dot, so a hyphenated RANGE like "2.2-2.4" yields 2.2 and 2.4 (both positive), not a
# spurious "-2.4"; a genuine " -2.4" (after a space) keeps its sign.
_DECIMAL = re.compile(r"(?<![\w.])-?\d[\d,]*\.\d+")
_PERCENT_INT = re.compile(r"(?<![\w.])-?\d[\d,]*(?=\s*%)")
# Cross-reference context: a number right after one of these is a POINTER (Figure 2.1, Eq. 3.4,
# Table 5, Section 2.2), not a measurement, so it is not required to survive into the spoken text.
_XREF = re.compile(
    r"(?i)\b(figs?|figure|figures|eqn?|eqs|equation|equations|tables?|sections?|sec|chapters?|"
    r"appendix|appendices|refs?|panels?)\.?\s*\(?\s*$"
)


class Violation(StrictModel):
    kind: str  # speakable | values | polarity | direction | paraphrase
    detail: str


class Verdict(StrictModel):
    ok: bool
    violations: list[Violation] = []


def _norm(text: str) -> str:
    """Lowercase, drop hyphens (so 'thirty-seven' == 'thirty seven'), collapse whitespace."""
    return " ".join(text.replace("-", " ").lower().split())


def _find_phrase(haystack: str, needle: str, start: int) -> int:
    """Word-boundary index of `needle` in `haystack` at or after `start`, else -1. Both are assumed
    already _norm-ed."""
    match = re.search(r"\b" + re.escape(needle) + r"\b", haystack[start:])
    return start + match.start() if match else -1


def _source_value_tokens(source: str) -> list[str]:
    """Decimals and percentage integers in source, in order - excluding cross-reference numbers
    (Figure 2.1, Eq. 3.4), which are pointers, not measurements."""
    found: list[tuple[int, str]] = []
    for m in _DECIMAL.finditer(source):
        before = source[max(0, m.start() - 24) : m.start()]
        if _XREF.search(before):
            continue  # a cross-reference (Figure 2.1), not a value to preserve
        if before.endswith("(") and source[m.end() : m.end() + 1] == ")":
            continue  # a lone parenthesized number, e.g. "(2.15)" - an equation/figure number
        found.append((m.start(), m.group()))
    for m in _PERCENT_INT.finditer(source):
        found.append((m.start(), m.group()))
    found.sort()
    return [tok for _, tok in found]


def _spell(token: str) -> str | None:
    try:
        return _norm(number_to_words(token))
    except (ValueError, IndexError):
        return None


def _verify_speakable(spoken: str) -> list[Violation]:
    bad = sorted({c for c in spoken if c not in _SPEAKABLE})
    if not bad:
        return []
    shown = " ".join(repr(c) for c in bad[:12])
    return [Violation(kind="speakable", detail=f"non-speakable characters in spoken text: {shown}")]


def _verify_values(source: str, spoken: str) -> list[Violation]:
    """Each source value (spelled by the oracle) must appear in the spoken text, in order. The
    oracle spells a leading '-' as "minus"; the narrator may voice it "negative", so the two are
    treated as the same sign here (a fully dropped sign still fails, catching a sign flip)."""
    body = re.sub(r"\bnegative\b", "minus", _norm(spoken))
    violations: list[Violation] = []
    cursor = 0
    for token in _source_value_tokens(source):
        canon = _spell(token)
        if canon is None:
            continue
        idx = _find_phrase(body, canon, cursor)
        if idx >= 0:
            cursor = idx + len(canon)
            continue
        # distinguish a dropped value from a reordered one
        if _find_phrase(body, canon, 0) < 0:
            violations.append(
                Violation(kind="values", detail=f"value {token!r} ({canon!r}) missing from spoken")
            )
        else:
            violations.append(
                Violation(kind="values", detail=f"value {token!r} ({canon!r}) out of order")
            )
    return violations


def _negations(text: str) -> Counter[str]:
    counts: Counter[str] = Counter(w for w in _WORD.findall(text.lower()) if w in _NEGATIONS)
    contractions = len(_NEG_CONTRACTION.findall(text.lower()))
    if contractions:
        counts["n't"] += contractions
    return counts


def _verify_counts(source: str, spoken: str) -> list[Violation]:
    """Relaxed, voicing-aware claim checks: negations exact, scope no-drop, direction net up/down.
    Permits the narrator to ADD direction/scope words when voicing symbols (< -> less, - ->
    negative) while still catching a dropped negation, a lost qualifier, or a reversed finding."""
    violations: list[Violation] = []

    src_neg, spk_neg = _negations(source), _negations(spoken)
    if src_neg != spk_neg:
        violations.append(
            Violation(
                kind="polarity", detail=f"negation changed: {dict(src_neg)} -> {dict(spk_neg)}"
            )
        )

    src_words = Counter(_WORD.findall(source.lower()))
    spk_words = Counter(_WORD.findall(spoken.lower()))
    dropped_scope = sorted(w for w in _SCOPE if spk_words[w] < src_words[w])
    if dropped_scope:
        violations.append(
            Violation(kind="polarity", detail=f"scope word(s) dropped: {dropped_scope}")
        )

    su = sum(src_words[w] for w in _UP)
    sd = sum(src_words[w] for w in _DOWN)
    ku = sum(spk_words[w] for w in _UP)
    kd = sum(spk_words[w] for w in _DOWN)
    flipped = (su > 0 and sd == 0 and kd > 0 and ku == 0) or (
        sd > 0 and su == 0 and ku > 0 and kd == 0
    )
    lost = su + sd > 0 and ku + kd == 0
    if flipped or lost:
        what = "reversed" if flipped else "lost"
        violations.append(
            Violation(
                kind="direction",
                detail=f"direction {what}: source up/down {su}/{sd} -> spoken {ku}/{kd}",
            )
        )
    return violations


def _verify_paraphrase(source: str, spoken: str) -> list[Violation]:
    src = content_words(source)
    spk = content_words(spoken)
    new_types = sorted(set(spk) - set(src))
    n_src = max(1, len(set(src)))
    if (
        len(new_types) > PARAPHRASE_MIN_NEW_TYPES
        and len(new_types) / n_src > PARAPHRASE_MAX_NEW_RATIO
    ):
        return [
            Violation(
                kind="paraphrase",
                detail=f"{len(new_types)} content words not in source: {new_types[:8]}",
            )
        ]
    return []


def verify_segment(source: str, spoken: str) -> Verdict:
    """Check a model-produced `spoken` rewrite against its `source` segment. ok=True means no floor
    invariant was broken (NOT a proof of faithfulness)."""
    violations = [
        *_verify_speakable(spoken),
        *_verify_values(source, spoken),
        *_verify_counts(source, spoken),
        *_verify_paraphrase(source, spoken),
    ]
    return Verdict(ok=not violations, violations=violations)
