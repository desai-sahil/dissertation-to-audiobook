"""The copy-edit safety guard: the deterministic floor for fixing the AUTHOR's own text.

When the script-repair writer is broadened past notation (to fix spelling typos, spacing/fusion,
and meaning-preserving grammar - Tier 1+2), this guard is what keeps a "typo fix" from silently
altering a claim. It is pure, deterministic, and replaces the old LLM faithfulness auditor (which
over-blocked). A pure-whitespace edit (splitting a fused word) is always allowed; otherwise an
author-text edit `find -> replace` is allowed ONLY if all of these hold:

1. VALUES preserved - the ordered sequence of digits AND of spoken value words (numbers, units,
   arithmetic connectives "per"/"times"/"squared", and Greek variable names "psi"/"alpha") is
   identical, so no value/sign/measurement/variable is changed, reordered, added, or dropped
   (numbers are words by phase 3, so a digit check alone is not enough).
2. POLARITY preserved - the count of each negation/scope word ("not", "no", "only", "all",
   "more", ...) is identical, so a claim can never be flipped or re-scoped.
3. DIRECTION preserved - the count of each directional/comparative result word ("increased",
   "higher", "positive", "above", ...) is identical, so a finding can never be reversed by a
   same-length antonym swap that the content check cannot see.
4. CONTENT conserved - at most ONE content word is substituted and none is net added or removed
   (function words like articles/auxiliaries may be added or removed freely for grammar). This
   allows a one-word typo fix and grammar agreement, but blocks paraphrase, inserting a hedge
   ("significant"), or dropping a content word.

A single content-word SUBSTITUTION (e.g. "responce" -> "response") is allowed and recorded in the
ledger for human review - the guard guarantees no number/polarity/claim-count change, and the
ledger + the Opus QC pass are the backstop for a rare bad in-place substitution. NOTATION edits
(cm -> centimeters) are NOT routed through this guard; they keep their trusted scope and are tagged
separately. This module has no I/O.
"""

from __future__ import annotations

import re
from collections import Counter

COPYEDIT_MAX_SPAN = 200  # an author-text find longer than this is not auto-applied

# Closed-class function words: freely added/removed when fixing grammar, because doing so does not
# change the claim (inserting "the", changing "is"->"are"). Everything not here and not a polarity
# word is treated as a CONTENT word whose add/remove is blocked.
_FUNCTION_WORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "yet", "so", "for", "of", "in", "on", "at", "to",
        "by", "with", "from", "into", "onto", "upon", "between", "among", "through", "during",
        "as", "than", "then", "thus",
        "it", "its", "this", "that", "these", "those", "they", "them", "their", "we", "our", "us",
        "he", "she", "his", "her", "him", "i", "you", "your", "which", "who", "whom", "whose",
        "there", "here", "is", "are", "was", "were", "be", "been", "being", "am", "has", "have",
        "had", "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may",
        "might", "must", "if", "while", "when", "where", "because", "since", "although", "though",
    }
)  # fmt: skip
# Polarity / scope words: their per-word COUNT must be preserved (adding or dropping one re-scopes
# or flips the meaning), so they are checked separately and excluded from both other classes.
_POLARITY_WORDS = frozenset(
    {
        "not", "no", "never", "none", "neither", "nor", "cannot", "without", "nothing", "nobody",
        "hardly", "scarcely", "barely", "only", "all", "every", "each", "both", "more", "less",
        "fewer", "most", "least", "non", "any", "some", "few", "many", "much",
    }
)  # fmt: skip
# Spelled-out numbers and value signs. By phase 3 the script reads numbers as WORDS ("five hundred
# twelve", "zero point one", "plus or minus"), so a one-word "typo" like "five" -> "nine" would
# otherwise pass the content check and silently change a value. Their ORDERED sequence is preserved
# (order matters: "two point five" must not become "five point two"), alongside the ASCII digits.
_NUMBER_WORDS = frozenset(
    {
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
        "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
        "hundred", "thousand", "million", "billion", "trillion", "point", "minus", "plus", "half",
        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
        "tenth",
        # magnitude / multiplier words that also carry a value
        "hundreds", "thousands", "millions", "billions", "dozen", "dozens", "fold", "decade",
        "decades", "quarter", "quarters", "thirds",
    }
)  # fmt: skip
# Spoken SI units (value-bearing): a "typo fix" must not swap "millimeters" -> "centimeters". Only
# unambiguous scientific units are listed; common-word time units (second/minute/hour/day) are
# omitted to avoid false-blocking a real typo of them.
_UNIT_WORDS = frozenset(
    {
        "millimeters", "millimeter", "centimeters", "centimeter", "meters", "meter", "kilometers",
        "micrometers", "micrometer", "nanometers", "nanometer", "angstrom", "angstroms",
        "molar", "millimolar", "micromolar", "moles", "micromoles", "millimoles", "nanomoles",
        "grams", "kilograms", "milligrams", "micrograms", "nanograms", "kilogram", "milligram",
        "pascals", "pascal", "kilopascals", "megapascals", "gigapascals", "bars", "millibars",
        "volts", "millivolts", "microvolts", "kilovolts", "ohms", "amperes", "milliamperes",
        "watts", "milliwatts", "kilowatts", "joules", "kilojoules", "newtons", "kelvin",
        "celsius", "fahrenheit", "degrees", "percent", "hertz", "kilohertz", "megahertz",
        "gigahertz", "liters", "milliliters", "microliters", "radians", "siemens", "tesla",
        "micromole", "millimole",
    }
)  # fmt: skip
# Spoken arithmetic / unit connectives and exponents: "per" vs "times" is division vs
# multiplication, "squared" vs "cubed" is a different exponent - all value-bearing, order-preserved.
_CONNECTIVE_WORDS = frozenset({"per", "times", "over", "divided", "squared", "cubed"})
# Spelled-out Greek letters: these ARE the variable/quantity names in this thesis ("water potential
# psi"), so swapping one ("psi" -> "phi") silently changes which quantity is meant. Order-preserved.
# (Mirror of curate._GREEK_NAMES; the Greek alphabet is fixed so the two cannot meaningfully drift.)
_NOTATION_WORDS = frozenset(
    {
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa",
        "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon", "phi",
        "chi", "psi", "omega",
    }
)  # fmt: skip
# Directional / comparative RESULT words: swapping one ("increased" -> "decreased", "higher" ->
# "lower", "positive" -> "negative", "above" -> "below") flips the author's finding with no number
# change, so their per-word COUNT is preserved (like polarity). A grammar edit that must change one
# is blocked and flagged for review instead - the conservative-safe choice for a claim.
_DIRECTION_WORDS = frozenset(
    {
        "increased", "decreased", "increase", "decrease", "increases", "decreases", "increasing",
        "decreasing", "rose", "fell", "rise", "fall", "rises", "falls", "risen", "fallen",
        "higher", "lower", "highest", "lowest", "greater", "greatest", "lesser",
        "positive", "negative", "positively", "negatively", "above", "below", "under",
        "before", "after", "faster", "slower", "doubled", "tripled", "halved", "quadrupled",
        "exceeded", "exceed", "gained", "lost", "gain", "loss", "upregulated", "downregulated",
    }
)  # fmt: skip
# All value-bearing spoken words: their ordered sequence is preserved (numbers, units, connectives,
# and Greek variable names all carry meaning; reordering or swapping one changes a measurement).
_VALUE_WORDS = _NUMBER_WORDS | _UNIT_WORDS | _CONNECTIVE_WORDS | _NOTATION_WORDS
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_NEG_CONTRACTION = re.compile(r"[A-Za-z]+n't\b", re.IGNORECASE)


def _digits(text: str) -> list[str]:
    """The ordered sequence of digit characters - equality means no ASCII number was altered."""
    return [c for c in text if c.isdigit()]


def _value_words(text: str) -> list[str]:
    """The ordered sequence of value-bearing words (numbers, units, connectives, Greek names) -
    equality blocks changing or reordering a value ("five" -> "nine", "two point five" -> "five
    point two", "millimeters" -> "centimeters", "per" -> "times", "psi" -> "phi")."""
    return [w.lower() for w in _WORD.findall(text) if w.lower() in _VALUE_WORDS]


def polarity_counts(text: str) -> Counter[str]:
    """Count of each negation/scope word, plus any "n't" contraction as a negation."""
    counts: Counter[str] = Counter(
        word.lower() for word in _WORD.findall(text) if word.lower() in _POLARITY_WORDS
    )
    n_contractions = len(_NEG_CONTRACTION.findall(text))
    if n_contractions:
        counts["n't"] += n_contractions
    return counts


def direction_counts(text: str) -> Counter[str]:
    """Count of each directional/comparative result word - equality blocks flipping a finding
    ("increased" -> "decreased", "above" -> "below") which a content-count check cannot see."""
    return Counter(word.lower() for word in _WORD.findall(text) if word.lower() in _DIRECTION_WORDS)


def content_words(text: str) -> Counter[str]:
    """Multiset of content words (lowercased): not function, polarity, value, or direction words."""
    return Counter(
        word.lower()
        for word in _WORD.findall(text)
        if word.lower() not in _FUNCTION_WORDS
        and word.lower() not in _POLARITY_WORDS
        and word.lower() not in _VALUE_WORDS
        and word.lower() not in _DIRECTION_WORDS
    )


def copyedit_guard(find: str, replace: str) -> bool:
    """True iff an author-text edit cannot change meaning. See the module docstring: values
    (digits + spelled-out numbers/units/connectives/Greek), polarity words, and directional result
    words are all preserved; content words change by at most one in-place substitution (function
    words may be freely added/removed)."""
    if not find.strip() or find == replace or len(find) > COPYEDIT_MAX_SPAN:
        return False
    # A pure whitespace change (split a fused word, fix spacing) only moves spaces, never the
    # characters, so it cannot alter a value or claim - always safe, whatever the words are.
    if re.sub(r"\s+", "", find) == re.sub(r"\s+", "", replace):
        return True
    if _digits(find) != _digits(replace):
        return False
    if _value_words(find) != _value_words(replace):
        return False
    if polarity_counts(find) != polarity_counts(replace):
        return False
    if direction_counts(find) != direction_counts(replace):
        return False
    before, after = content_words(find), content_words(replace)
    removed = before - after
    added = after - before
    return sum(removed.values()) == sum(added.values()) <= 1
