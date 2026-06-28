"""The domain lexicon: a pure, versioned, reusable artifact (zero I/O).

For M1 the default plant-physiology lexicon is embedded as data. Loading from a
versioned file and publishing to an ElevenLabs pronunciation dictionary land in M5.
Entries are alias expansions: a grapheme maps to its spoken form. The orchestrator
applies all alias categories in one longest-grapheme-first pass so that compound
terms (GhSLAC1, PYR-PP2C-OST1-SLAC1) win over their substrings.

Gene and mutant pronunciation follows the "letters plus number" convention by
default (slac1 -> "S L A C one"). This is a lab-convention judgment call flagged for
the user; change the `spoken` values here to switch conventions.
"""

from __future__ import annotations

import re
from typing import Literal

from thesis_audiobook.ir import StrictModel

LexCategory = Literal["symbol", "gene", "acronym", "greek", "unit", "errata"]


class LexEntry(StrictModel):
    grapheme: str
    spoken: str
    category: LexCategory
    case_sensitive: bool = True
    word_boundaries: bool = True


class Lexicon(StrictModel):
    version: str = "plant-physiology-v0"
    entries: list[LexEntry] = []

    def by_category(self, *categories: LexCategory) -> list[LexEntry]:
        wanted = set(categories)
        return [entry for entry in self.entries if entry.category in wanted]

    def alias_entries(self) -> list[LexEntry]:
        """All expandable categories, longest grapheme first (global longest match)."""
        alias = self.by_category("symbol", "gene", "acronym", "greek", "errata")
        return sorted(alias, key=lambda entry: len(entry.grapheme), reverse=True)


def apply_entries(text: str, entries: list[LexEntry]) -> str:
    """Replace each grapheme with its spoken form. Caller controls entry ordering."""
    for entry in entries:
        flags = 0 if entry.case_sensitive else re.IGNORECASE
        grapheme = re.escape(entry.grapheme)
        if entry.word_boundaries:
            pattern = rf"(?<![A-Za-z0-9]){grapheme}(?![A-Za-z0-9])"
        else:
            pattern = grapheme
        spoken = entry.spoken
        text = re.sub(pattern, lambda _match, value=spoken: value, text, flags=flags)
    return text


def apply_lexicon(text: str, lexicon: Lexicon) -> str:
    """Apply every alias category in one global longest-match pass."""
    return apply_entries(text, lexicon.alias_entries())


def _e(
    grapheme: str,
    spoken: str,
    category: LexCategory,
    *,
    case_sensitive: bool = True,
) -> LexEntry:
    return LexEntry(
        grapheme=grapheme, spoken=spoken, category=category, case_sensitive=case_sensitive
    )


_ENTRIES: list[LexEntry] = [
    # Symbols and variables (always voiced).
    _e("gs", "stomatal conductance", "symbol"),
    _e("g_s", "stomatal conductance", "symbol"),
    _e("goxz", "outside-xylem conductance", "symbol"),
    _e("g_oxz", "outside-xylem conductance", "symbol"),
    _e("A_n", "net assimilation rate", "symbol"),
    _e("WUE", "water use efficiency", "symbol"),
    # Greek-domain expansions (win over the bare greek letter).
    _e("psi_xyl", "xylem water potential", "greek"),
    _e("psixyl", "xylem water potential", "greek"),
    _e("ψ_xyl", "xylem water potential", "greek"),
    _e("ψxyl", "xylem water potential", "greek"),
    _e("psi_ssc^apo", "apoplastic subsidiary-cell water potential", "greek"),
    _e("ψ_ssc^apo", "apoplastic subsidiary-cell water potential", "greek"),
    _e("ψssc^apo", "apoplastic subsidiary-cell water potential", "greek"),
    _e("psi_ssc", "subsidiary-cell water potential", "greek"),
    _e("ψ_ssc", "subsidiary-cell water potential", "greek"),
    # Gene and mutant names. Field convention: pronounceable roots are voiced as
    # words (slac1 -> "slac one", osca1 -> "osca one"); initialisms are spelled as
    # letters (cpk -> "C P K", OST1 -> "O S T one"). Override individual entries here.
    _e("GhSLAC1", "G H slac one", "gene"),
    _e("SLAC1", "slac one", "gene"),
    _e("slac1", "slac one", "gene"),
    _e("OSCA1", "osca one", "gene"),
    _e("osca1", "osca one", "gene"),
    _e("OST1", "O S T one", "gene"),
    _e("ost1", "O S T one", "gene"),
    _e("CPK", "C P K", "gene"),
    _e("cpk", "C P K", "gene"),
    _e("aao3", "A A O three", "gene"),
    # Acronyms that expand.
    _e("ABA", "abscisic acid", "acronym"),
    _e("ROS", "reactive oxygen species", "acronym"),
    _e("OXZ", "outside xylem", "acronym"),
    _e("SPAC", "soil plant atmosphere continuum", "acronym"),
    _e("VPD", "vapor pressure deficit", "acronym"),
    _e("FDR", "false discovery rate", "acronym"),
    _e("WT", "wild type", "acronym"),
    _e("SSC", "subsidiary cell", "acronym"),
    # Acronyms spelled as letters.
    _e("MCMC", "M C M C", "acronym"),
    _e("ODE", "O D E", "acronym"),
    _e("PYR-PP2C-OST1-SLAC1", "P Y R, P P two C, O S T one, slac one", "acronym"),
    _e("PYR–PP2C–OST1–SLAC1", "P Y R, P P two C, O S T one, slac one", "acronym"),
    _e("HP-HA", "hydropassive hydroactive", "acronym"),
    _e("HP–HA", "hydropassive hydroactive", "acronym"),
    _e("PP2C", "P P two C", "acronym"),
    _e("PYR", "P Y R", "acronym"),
    # Errata: unambiguous source misspellings of common words, corrected so they are not read
    # aloud wrong. Only scale-words and the like, where the correction changes no number/name/claim.
    _e("billons", "billion", "errata", case_sensitive=False),
    _e("millons", "million", "errata", case_sensitive=False),
]

DEFAULT_LEXICON = Lexicon(version="plant-physiology-v0", entries=_ENTRIES)
