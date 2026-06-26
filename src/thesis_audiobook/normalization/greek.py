"""Greek letters. Pure, deterministic, no I/O.

Domain expansions from the lexicon (psi_xyl -> "xylem water potential") win first;
residual bare letters fall back to their names (psi, delta).
"""

from __future__ import annotations

from thesis_audiobook.lexicon import Lexicon, apply_entries

_GREEK_LETTERS: dict[str, str] = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho",
    "σ": "sigma", "ς": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi",
    "χ": "chi", "ψ": "psi", "ω": "omega",
    "Δ": "delta", "Φ": "phi", "Ψ": "psi", "Σ": "sigma", "Ω": "omega",
    "Θ": "theta", "Λ": "lambda", "Π": "pi", "Γ": "gamma",
    "μ": "mu", "µ": "mu",
}  # fmt: skip


def expand_greek_letters(text: str) -> str:
    for letter, name in _GREEK_LETTERS.items():
        text = text.replace(letter, f" {name} ")
    return text


def expand_greek(text: str, lexicon: Lexicon) -> str:
    entries = sorted(
        lexicon.by_category("greek"), key=lambda entry: len(entry.grapheme), reverse=True
    )
    return expand_greek_letters(apply_entries(text, entries))
