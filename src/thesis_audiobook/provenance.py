"""Pure provenance: map audiobook timeline back to source block ids. No I/O.

assemble_audio builds this from per-chunk durations (reported by the muxer) and each
chunk's source block ids, then the CLI writes it as a sidecar JSON next to the M4B.
It round-trips: parse(serialize(map)) == map.
"""

from __future__ import annotations

from thesis_audiobook.ir import StrictModel


class ProvenanceSegment(StrictModel):
    chunk_id: str
    chapter: int | None
    block_ids: list[str]
    start_seconds: float
    end_seconds: float


class ProvenanceMap(StrictModel):
    segments: list[ProvenanceSegment] = []


def build_provenance(
    entries: list[tuple[str, int | None, list[str], float]],
) -> ProvenanceMap:
    """Lay chunk durations end to end into a timeline.

    Each entry is (chunk_id, chapter, block_ids, seconds), in play order. Times are
    rounded to the millisecond so the map is byte-stable across runs.
    """
    segments: list[ProvenanceSegment] = []
    cursor = 0.0
    for chunk_id, chapter, block_ids, seconds in entries:
        start = round(cursor, 3)
        end = round(cursor + seconds, 3)
        segments.append(
            ProvenanceSegment(
                chunk_id=chunk_id,
                chapter=chapter,
                block_ids=list(block_ids),
                start_seconds=start,
                end_seconds=end,
            )
        )
        cursor = end
    return ProvenanceMap(segments=segments)


def block_ids_at(provenance: ProvenanceMap, seconds: float) -> list[str]:
    """The source block ids playing at a given timestamp (empty if past the end)."""
    for segment in provenance.segments:
        if segment.start_seconds <= seconds < segment.end_seconds:
            return segment.block_ids
    return []
