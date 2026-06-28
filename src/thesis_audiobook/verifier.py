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
  3. POLARITY   - negation/scope word counts are preserved (reuse copyedit), so a claim cannot flip.
  4. DIRECTION  - increase/decrease/comparison word counts are preserved (reuse copyedit).
  5. PARAPHRASE - the spoken text does not inject many content words absent from the source, which
                  catches free composition / a hallucinated clause (a constrained rewrite stays
                  close to the source wording).

The model only writes; this only checks. A violation routes the segment to regenerate, then escalate
to human review. Pure, no I/O. Intended to be the most-tested module in the package.
"""

from __future__ import annotations

import re
import string

# Reuse the copy-edit guard's claim-safety helpers (same package; intentional shared seed).
from thesis_audiobook.copyedit import content_words, direction_counts, polarity_counts
from thesis_audiobook.ir import StrictModel
from thesis_audiobook.normalization.numbers import number_to_words

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
    | {"–", "‘", "’", "“", "”", "…"}  # en dash, smart quotes, ellipsis
)

# Value tokens whose change would alter a claim: decimals (measurements, ratios, p-values) and
# integers written as a percentage. Bare integers are intentionally out of scope (see module docs).
_DECIMAL = re.compile(r"-?\d[\d,]*\.\d+")
_PERCENT_INT = re.compile(r"-?\d[\d,]*(?=\s*%)")


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
    """Decimals and percentage integers in source, in order of appearance."""
    found: list[tuple[int, str]] = []
    for m in _DECIMAL.finditer(source):
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
    """Each source value (spelled by the oracle) must appear in the spoken text, in order."""
    body = _norm(spoken)
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


def _verify_counts(source: str, spoken: str) -> list[Violation]:
    violations: list[Violation] = []
    if polarity_counts(source) != polarity_counts(spoken):
        violations.append(
            Violation(
                kind="polarity",
                detail=f"negation/scope changed: {dict(polarity_counts(source))} -> "
                f"{dict(polarity_counts(spoken))}",
            )
        )
    if direction_counts(source) != direction_counts(spoken):
        violations.append(
            Violation(
                kind="direction",
                detail=f"direction words changed: {dict(direction_counts(source))} -> "
                f"{dict(direction_counts(spoken))}",
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
