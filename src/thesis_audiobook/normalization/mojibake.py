"""Repair OCR mojibake: detached diacritics from PDF text recognition. Pure, no I/O.

Marker's OCR sometimes emits an accent as a SEPARATE token, detached from its base letter:
"Scholander ¨", "Forster ¨", "the Forster en- ¨ ergy", "inter- ´ faces". Read aloud these
are garbled. We NFC-normalize (recombining any decomposed but ATTACHED accents, which are
fine), then remove only DETACHED marks - those preceded by a space or sitting in a
hyphenation split - so genuine accented characters (é, ö) are untouched. No-op on clean
prose, so it is safe to run parser-agnostically in build_ir.
"""

from __future__ import annotations

import re
import unicodedata

# Spacing diacritics (U+00A8 diaeresis, U+00B4 acute, U+02C6 circumflex, U+02DC tilde) plus
# the combining-marks block (U+0300-U+036F), as they appear DETACHED in OCR output.
_MARKS = "¨´ˆ˜̀-ͯ"
_HAS_MARK = re.compile(f"[{_MARKS}]")
# "en- ¨ ergy" / "inter- ´ faces": a hyphenation split with a stray mark in the gap.
_HYPHEN_MARK = re.compile(rf"(?<=\w)-\s*[{_MARKS}]+\s*(?=\w)")
# "Scholander ¨" / "Scholander ¨.": a mark detached after a word (space before, non-word after).
_DETACHED = re.compile(rf"\s+[{_MARKS}]+(?=\s|$|[^\w{_MARKS}])")


def fix_mojibake(text: str) -> str:
    if not text or not _HAS_MARK.search(text):
        # Fast path: NFC only matters when a combining mark is present; nothing to do.
        return unicodedata.normalize("NFC", text) if text else text
    text = unicodedata.normalize("NFC", text)
    text = _HYPHEN_MARK.sub("", text)
    text = _DETACHED.sub("", text)
    return " ".join(text.split())
