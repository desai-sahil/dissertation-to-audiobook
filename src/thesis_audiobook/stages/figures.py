"""Stage: figure caption verbalizer and table handler.

Captions: cleaned for the ear ("Fig. 3" -> "Figure 3", "(A)" -> "Panel A"), normalized,
and stored on the figure; assemble_script places them at the first in-text reference.

Tables, driven by the profile's table_handling:
  - summarize (committee): feed the table to the LlmClient, speak the one returned
    summary sentence (run back through the normalizer for the no-leak invariant).
    handling=summarize.
  - skip (general): a one-line note, no LLM call. handling=skip.

The LlmClient is mocked in tests; the cost guard fails any accidental real call.
"""

from __future__ import annotations

import re

from thesis_audiobook.context import Context
from thesis_audiobook.ir import BlockType, Document, Handling
from thesis_audiobook.lexicon import Lexicon
from thesis_audiobook.normalization import normalize_all
from thesis_audiobook.normalization.numbers import number_to_words

_FIG = re.compile(r"\bFig\.\s*", re.IGNORECASE)
_PANEL = re.compile(r"\(([A-Za-z])\)")


def clean_caption(caption: str, lexicon: Lexicon) -> str:
    caption = _FIG.sub("Figure ", caption)
    caption = _PANEL.sub(lambda m: f"Panel {m.group(1).upper()}", caption)
    return normalize_all(caption, lexicon)


def table_summary_prompt(raw: str) -> str:
    return (
        "Here is a table from a scientific thesis:\n\n"
        f"{raw}\n\n"
        "In one spoken sentence for an audiobook, summarize what this table reports."
    )


class FiguresStage:
    name = "figures"

    def run(self, doc: Document, ctx: Context) -> Document:
        for figure in doc.figures.values():
            figure.spoken = clean_caption(figure.caption, ctx.lexicon)

        summarize = ctx.config.profile.table_handling == "summarize"
        number = 0
        for block in doc.blocks:
            if block.type is not BlockType.table or not block.keep:
                continue
            number += 1
            label = f"Table {number_to_words(str(number))}"
            if summarize:
                summary = normalize_all(
                    ctx.llm.complete(table_summary_prompt(block.text)), ctx.lexicon
                )
                block.spoken = f"{label}. {summary}"
                block.handling = Handling.summarize
            else:
                block.spoken = f"{label} is omitted from the audio."
                block.handling = Handling.skip
        return doc
