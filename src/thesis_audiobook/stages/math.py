"""Stage: math and notation transformer (display equations). Pure, no I/O.

Driven by the profile's equation_tier:
  - announce (default): the formula is NOT read aloud. A numbered equation (one carrying a
    LaTeX \\tag{X.Y}, or a trailing "(X.Y)" line folded into it upstream) is announced by its
    real number ("Equation two point four.") so the audio matches the prose's "in Equation 2.4"
    references. An unnumbered display equation (an intermediate derivation step) is dropped from
    the audio, since there is no formula read and no number to announce.
  - full: not implemented yet (spoken math via MathCAT/SRE) - a clear error path.

There is no LLM call here: glossing a formula into prose was the one place the pipeline let a
model write spoken text from scratch, and it could go off-domain. Announcing the number is
deterministic and claim-safe. Inline symbols stay with the M1 normalizer/lexicon.
"""

from __future__ import annotations

import re

from thesis_audiobook.context import Context
from thesis_audiobook.ir import BlockType, Document, Handling
from thesis_audiobook.normalization.numbers import section_to_words

# A real equation number: \tag{2.4}, or a bare "(2.4)" that upstream folded into the LaTeX.
_TAG = re.compile(r"\\tag\{\s*\(?\s*([0-9]+(?:\.[0-9]+)*)\s*\)?\s*\}")
_TRAILING_NUMBER = re.compile(r"\(\s*([0-9]+(?:\.[0-9]+)+)\s*\)\s*$")


def equation_number(latex: str) -> str | None:
    """Extract the thesis's own equation number from a display equation's LaTeX, or None."""
    match = _TAG.search(latex) or _TRAILING_NUMBER.search(latex.strip())
    return match.group(1) if match else None


class MathStage:
    name = "math"

    def run(self, doc: Document, ctx: Context) -> Document:
        tier = ctx.config.profile.equation_tier
        if tier == "full":
            raise NotImplementedError(
                "equation_tier 'full' (spoken math via MathCAT/SRE) is not implemented yet"
            )
        for block in doc.blocks:
            if block.type is not BlockType.equation_display or not block.keep:
                continue
            number = equation_number(block.latex or block.text)
            if number is None:
                # An unnumbered intermediate step: nothing to announce, drop it from the audio.
                block.spoken = None
                block.handling = Handling.skip
                block.keep = False
                continue
            block.spoken = f"Equation {section_to_words(number)}."
            block.handling = Handling.announce
        return doc
