"""Numerals, ranges, exponents, percent. Pure, deterministic, no I/O.

Number-to-words is total: every digit run is converted, so no digits survive (which
keeps the normalizer idempotent and the no-leak invariant easy to hold).
"""

from __future__ import annotations

import re

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]  # fmt: skip
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_SCALES = [(1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")]


def _below_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")


def _below_thousand(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts: list[str] = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} hundred")
    if rest:
        parts.append(_below_hundred(rest))
    return " ".join(parts)


def _digits_to_words(digits: str) -> str:
    return " ".join(_ONES[int(d)] for d in digits)


def int_to_words(n: int) -> str:
    if n < 0:
        return f"minus {int_to_words(-n)}"
    if n == 0:
        return "zero"
    if n > 999_999_999:
        return _digits_to_words(str(n))
    parts: list[str] = []
    for value, name in _SCALES:
        if n >= value:
            quotient, n = divmod(n, value)
            parts.append(f"{_below_thousand(quotient)} {name}")
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def year_to_words(year: int) -> str:
    """Read a calendar year in pairs: 2019 -> 'twenty nineteen', 2005 -> 'two thousand five'."""
    if not 1000 <= year <= 2999:
        return int_to_words(year)
    high, low = divmod(year, 100)
    if low == 0:
        return int_to_words(year) if high % 10 == 0 else f"{int_to_words(high)} hundred"
    if 2000 <= year <= 2009:
        return f"two thousand {_ONES[low]}"
    tail = f"oh {_ONES[low]}" if low < 10 else _below_hundred(low)
    return f"{int_to_words(high)} {tail}"


def number_to_words(token: str) -> str:
    """Convert a numeric token (integer or decimal, optional leading minus)."""
    sign = ""
    if token.startswith("-"):
        sign, token = "minus ", token[1:]
    token = token.replace(",", "")
    if "." in token:
        whole, _, frac = token.partition(".")
        whole_words = int_to_words(int(whole)) if whole else "zero"
        frac_words = _digits_to_words(frac) if frac else ""
        spoken = f"{whole_words} point {frac_words}".strip()
    else:
        spoken = int_to_words(int(token)) if token else ""
    return f"{sign}{spoken}".strip()


def section_to_words(section: str) -> str:
    """Speak a hierarchical section number like '2.3.1' as 'two point three point one'.

    Each dot-separated component is read as an integer ('6.10' -> 'six point ten'), not as
    digits. Non-numeric or empty components are skipped/passed through so a messy heading
    never raises (number_to_words crashes on multi-dot section numbers; this does not).
    """
    words: list[str] = []
    for part in section.split("."):
        part = part.strip()
        if part.isdigit():
            words.append(int_to_words(int(part)))
        elif part:
            words.append(part)
    return " point ".join(words) if words else section.strip()


def _spell_exponent(exp: str) -> str:
    if exp == "2":
        return " squared"
    if exp == "3":
        return " cubed"
    return f" to the {number_to_words(exp)}"


def handle_superscripts(text: str) -> str:
    # ^{...} or ^N or ^-N (math exponents; chemistry/units are handled earlier).
    return re.sub(r"\^\{?(-?\d+)\}?", lambda m: _spell_exponent(m.group(1)), text)


def handle_subscripts(text: str) -> str:
    # Residual subscripts after lexicon expansion: x_i -> "x i".
    return re.sub(r"_\{?([A-Za-z0-9]+)\}?", lambda m: f" {m.group(1)}", text)


def handle_ranges(text: str) -> str:
    # A hyphen or en/em dash directly between two numbers is a range.
    return re.sub(
        r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)",
        r"\1 to \2",
        text,
    )


def handle_negatives(text: str) -> str:
    # A dash immediately before a digit, not preceded by an alphanumeric, is minus.
    return re.sub(r"(?<![A-Za-z0-9])[-−](?=\d)", "minus ", text)


def handle_percent(text: str) -> str:
    return text.replace("%", " percent")


def spell_numbers(text: str) -> str:
    # Standalone numbers (no letter or digit on either side, so the whole run is
    # consumed) become cardinal words. A trailing "." or "," is left alone so
    # sentence periods and list commas survive.
    standalone = r"(?<![A-Za-z0-9])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![A-Za-z0-9])"
    text = re.sub(standalone, lambda m: number_to_words(m.group(0)), text)
    # A quantity glued to a following word (56mM, 10x): cardinal, split off the word
    # so the unit/word can be matched on the next normalization pass.
    text = re.sub(
        r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)(?=[A-Za-z])",
        lambda m: f"{number_to_words(m.group(1))} ",
        text,
    )
    # Digits embedded after letters (C3, A8H, CYP707A) are read digit by digit,
    # spaced off the letters so they do not glue into "Cthree".
    return re.sub(r"\d+", lambda m: f" {_digits_to_words(m.group(0))} ", text)


_SUPERSCRIPT = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6",
    "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-", "⁺": "+",
}  # fmt: skip
_SUBSCRIPT = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6",
    "₇": "7", "₈": "8", "₉": "9",
}  # fmt: skip


def unicode_exponents_to_ascii(text: str) -> str:
    """Convert residual unicode super/subscripts to ASCII (chemistry handled earlier)."""
    text = re.sub(
        r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+",
        lambda m: "^" + "".join(_SUPERSCRIPT[c] for c in m.group(0)),
        text,
    )
    text = re.sub(
        r"[₀₁₂₃₄₅₆₇₈₉]+",
        lambda m: "".join(_SUBSCRIPT[c] for c in m.group(0)),
        text,
    )
    return text


def normalize_numbers(text: str) -> str:
    text = unicode_exponents_to_ascii(text)
    text = handle_superscripts(text)
    text = handle_subscripts(text)
    text = handle_ranges(text)
    text = handle_negatives(text)
    text = handle_percent(text)
    text = spell_numbers(text)
    return text
