"""Stage: audio assembler.

Builds a pure AudiobookPlan (chapters, ordered chunk ids, metadata) from the document
and hands it, with the rendered chunk bytes, to the AudioMuxer port. The muxer (ffmpeg
in production, a pure stand-in in tests) returns the finished file blobs and per-chunk
timings; the stage turns the timings into the provenance map. All of that lands on the
Context; the CLI composition root performs the filesystem writes. The stage itself does
no subprocess or file I/O - that lives in the FfmpegMuxer adapter behind the port.
"""

from __future__ import annotations

import re
from itertools import groupby

from thesis_audiobook.context import Context
from thesis_audiobook.ir import BlockType, Document
from thesis_audiobook.normalization.numbers import int_to_words
from thesis_audiobook.ports.audio import AudiobookPlan, ChapterSpec
from thesis_audiobook.provenance import build_provenance


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "thesis"


def _chapter_title(doc: Document, chapter: int | None) -> str:
    if chapter is None:
        return "Front matter"
    for block in doc.blocks:
        if block.type is BlockType.heading and block.chapter == chapter and block.section is None:
            return block.current_text()
    return f"Chapter {int_to_words(chapter)}"


def _resolved_chapters(doc: Document) -> list[int | None]:
    """Assign each chunk a chapter, folding front/back matter into a real chapter.

    The script stage brackets the body with a chapter=None intro and outro, and chapter
    boundaries can leave None chunks between chapters. Left raw, those split a chapter
    into several markers and shift chapter numbers. So a None chunk rides with the
    preceding real chapter (or, before any chapter, the first one). The result is exactly
    one contiguous run per chapter, in reading order, with no spurious markers.
    """
    forward: list[int | None] = []
    last: int | None = None
    for chunk in doc.chunks:
        if chunk.chapter is not None:
            last = chunk.chapter
        forward.append(last)
    first_real = next((chunk.chapter for chunk in doc.chunks if chunk.chapter is not None), None)
    return [chapter if chapter is not None else first_real for chapter in forward]


def build_audiobook_plan(doc: Document, ctx: Context) -> AudiobookPlan:
    resolved = _resolved_chapters(doc)
    chapters: list[ChapterSpec] = []
    for chapter_value, group in groupby(range(len(doc.chunks)), key=lambda i: resolved[i]):
        chunk_ids = [doc.chunks[i].id for i in group]
        chapters.append(
            ChapterSpec(
                index=len(chapters) + 1,
                title=_chapter_title(doc, chapter_value),
                chunk_ids=chunk_ids,
            )
        )
    return AudiobookPlan(
        title=doc.meta.title,
        author=doc.meta.author,
        narrator=ctx.config.narrator,
        slug=slugify(doc.meta.title),
        output_mode=ctx.config.output_mode,
        chapters=chapters,
    )


class AssembleAudioStage:
    name = "assemble_audio"

    def run(self, doc: Document, ctx: Context) -> Document:
        plan = build_audiobook_plan(doc, ctx)
        result = ctx.muxer.mux(plan, ctx.rendered)

        ctx.audio_outputs = result.outputs
        ctx.chapter_count = result.chapter_count
        ctx.final_audio = result.outputs[0].data if result.outputs else b""

        by_id = {chunk.id: chunk for chunk in doc.chunks}
        entries = [
            (
                timing.chunk_id,
                by_id[timing.chunk_id].chapter,
                by_id[timing.chunk_id].block_ids,
                timing.seconds,
            )
            for timing in result.timings
            if timing.chunk_id in by_id
        ]
        ctx.provenance = build_provenance(entries)
        ctx.log.info(
            "audio_assembled",
            chapters=result.chapter_count,
            outputs=len(result.outputs),
        )
        return doc
