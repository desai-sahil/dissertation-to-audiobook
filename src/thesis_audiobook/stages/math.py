"""Stage: math and notation transformer (display equations).

Driven by the profile's equation_tier:
  - gloss (committee): feed the equation's LaTeX to the LlmClient and speak the one
    returned sentence describing what the equation expresses. handling=gloss.
  - announce (general): no LLM call; a short spoken pointer. handling=announce.
  - full: not implemented yet (spoken math via MathCAT/SRE) - a clear error path.

The gloss is run back through the deterministic normalizer so the no-leak invariant
holds even if the model returns stray notation. Inline symbols stay with the M1
normalizer/lexicon and are not re-handled here. The LlmClient is mocked in tests, so
no real LLM call happens off the live path; the cost guard makes any accidental real
call fail.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import BlockType, Document, Handling
from thesis_audiobook.normalization import normalize_all
from thesis_audiobook.normalization.numbers import number_to_words


def gloss_prompt(latex: str) -> str:
    return (
        "Here is a display equation from a scientific thesis, in LaTeX:\n\n"
        f"{latex}\n\n"
        "In one spoken sentence for an audiobook, say what this equation expresses "
        "(its meaning), not how it is typeset."
    )


class MathStage:
    name = "math"

    def run(self, doc: Document, ctx: Context) -> Document:
        tier = ctx.config.profile.equation_tier
        number = 0
        for block in doc.blocks:
            if block.type is not BlockType.equation_display or not block.keep:
                continue
            number += 1
            label = f"Equation {number_to_words(str(number))}"
            if tier == "gloss":
                gloss = normalize_all(
                    ctx.llm.complete(gloss_prompt(block.latex or block.text)), ctx.lexicon
                )
                block.spoken = f"{label}. {gloss}"
                block.handling = Handling.gloss
            elif tier == "announce":
                block.spoken = f"{label} is shown in the text here."
                block.handling = Handling.announce
            else:  # "full"
                raise NotImplementedError(
                    "equation_tier 'full' (spoken math via MathCAT/SRE) is not implemented yet"
                )
        return doc
