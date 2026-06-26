"""Stage: script assembler.

Builds the reviewable script and the chunk plan from the normalized blocks:
  - an intro (title, author) and a short outro;
  - structural announcements ("Chapter one.", "Section six point two, Results.");
  - figure captions placed at their first in-text reference point;
  - break tags after headings where the voice model honors them.

The script is exactly the concatenation of its segments, and the chunk planner
partitions those segments, so the chunk-conservation invariant holds by construction.
"""

from __future__ import annotations

from thesis_audiobook.chunking import ScriptSegment, plan_chunks
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.lexicon import Lexicon
from thesis_audiobook.normalization import normalize_all
from thesis_audiobook.normalization.numbers import int_to_words, section_to_words

_BREAK = '<break time="0.8s"/>'
_GAP = "\n\n"


def model_supports_breaks(model_id: str) -> bool:
    # multilingual_v2 honors SSML break tags; v3 does not.
    return "v3" not in model_id


def _heading_announcement(block: Block) -> str:
    title = block.current_text()
    if block.section:
        return f"Section {section_to_words(block.section)}, {title}."
    if block.chapter is not None:
        return f"Chapter {int_to_words(block.chapter)}. {title}."
    return f"{title}."


def _render_block(block: Block) -> str | None:
    if block.type is BlockType.heading:
        return _heading_announcement(block)
    if block.spoken:
        return block.spoken
    return None


class AssembleScriptStage:
    name = "assemble_script"

    def run(self, doc: Document, ctx: Context) -> Document:
        lexicon = ctx.lexicon
        breaks = model_supports_breaks(ctx.config.profile.model_id)
        segments: list[ScriptSegment] = []

        intro = self._intro(doc.meta, lexicon)
        segments.append(ScriptSegment(text=intro + _GAP))
        if breaks:
            segments.append(ScriptSegment(text=_BREAK + _GAP))

        first_ref: dict[str, list[str]] = {}
        for figure_id, figure in doc.figures.items():
            if figure.ref_points:
                first_ref.setdefault(figure.ref_points[0], []).append(figure_id)
        placed: set[str] = set()

        for block in doc.blocks:
            if not block.keep:
                continue
            rendered = _render_block(block)
            if rendered is None:
                continue
            segments.append(
                ScriptSegment(text=rendered + _GAP, block_id=block.id, chapter=block.chapter)
            )
            if block.type is BlockType.heading and breaks:
                segments.append(ScriptSegment(text=_BREAK + _GAP, chapter=block.chapter))
            for figure_id in first_ref.get(block.id, []):
                caption = doc.figures[figure_id].spoken
                if caption:
                    segments.append(ScriptSegment(text=caption + _GAP, chapter=block.chapter))
                    placed.add(figure_id)

        for figure_id, figure in doc.figures.items():
            if figure_id not in placed and figure.spoken:
                segments.append(ScriptSegment(text=figure.spoken + _GAP))

        segments.append(ScriptSegment(text=self._outro(doc.meta, lexicon)))

        doc.script = "".join(segment.text for segment in segments)
        doc.chunks = plan_chunks(segments, ctx.config.chunk_char_limit)
        return doc

    def _intro(self, meta: DocumentMeta, lexicon: Lexicon) -> str:
        author = f", by {meta.author}" if meta.author else ""
        text = f"An audiobook rendering of {meta.title}{author}."
        return normalize_all(text, lexicon)

    def _outro(self, meta: DocumentMeta, lexicon: Lexicon) -> str:
        return normalize_all(f"This concludes {meta.title}.", lexicon)
