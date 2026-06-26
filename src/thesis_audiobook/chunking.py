"""The chunk planner: split the script into TTS-sized chunks. Pure, no I/O.

Conservation invariant: concatenating chunk texts reproduces the input exactly (no
characters added, dropped, or duplicated). Every chunk stays at or under the limit,
and neighbor pointers are consistent. Chunks carry source block ids for provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from thesis_audiobook.ir import Chunk
from thesis_audiobook.normalization.segmentation import segment


@dataclass(frozen=True)
class ScriptSegment:
    text: str
    block_id: str | None = None
    chapter: int | None = None


def _hard_split(segments: list[ScriptSegment], limit: int) -> list[ScriptSegment]:
    pieces: list[ScriptSegment] = []
    for seg in segments:
        if len(seg.text) <= limit:
            pieces.append(seg)
            continue
        for start in range(0, len(seg.text), limit):
            pieces.append(replace(seg, text=seg.text[start : start + limit]))
    return pieces


def plan_chunks(segments: list[ScriptSegment], limit: int) -> list[Chunk]:
    if limit < 1:
        raise ValueError("chunk char limit must be at least 1")

    chunks: list[Chunk] = []
    text = ""
    block_ids: list[str] = []
    chapter: int | None = None

    def flush() -> None:
        nonlocal text, block_ids, chapter
        if not text:
            return
        chunks.append(
            Chunk(
                id=f"chunk.{len(chunks) + 1}",
                text=text,
                chapter=chapter,
                block_ids=block_ids,
            )
        )
        text, block_ids, chapter = "", [], None

    for piece in _hard_split(segments, limit):
        if text and len(text) + len(piece.text) > limit:
            flush()
        if not text:
            chapter = piece.chapter
        text += piece.text
        if piece.block_id is not None and piece.block_id not in block_ids:
            block_ids.append(piece.block_id)
    flush()

    for index, chunk in enumerate(chunks):
        chunk.prev_id = chunks[index - 1].id if index > 0 else None
        chunk.next_id = chunks[index + 1].id if index + 1 < len(chunks) else None
    return chunks


def plan_chunks_from_text(text: str, limit: int) -> list[Chunk]:
    """Convenience for tests: segment a flat string, then plan."""
    return plan_chunks([ScriptSegment(text=part) for part in segment(text)], limit)


def preview_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """Keep only the first chapter (plus any leading front matter) and re-link neighbors.

    Powers `--preview`: render the opening of the book without paying for the whole
    thing. On a single-chapter input this returns every chunk unchanged.
    """
    first_chapter = next((chunk.chapter for chunk in chunks if chunk.chapter is not None), None)
    kept = [chunk for chunk in chunks if chunk.chapter in (None, first_chapter)]
    for index, chunk in enumerate(kept):
        chunk.prev_id = kept[index - 1].id if index > 0 else None
        chunk.next_id = kept[index + 1].id if index + 1 < len(kept) else None
    return kept
