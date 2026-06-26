"""AudioMuxer port: assemble rendered chunk audio into the deliverable.

The assemble_audio stage builds a pure AudiobookPlan (chapters, ordered chunk ids,
metadata) and hands it plus the rendered chunk bytes to this port. The muxer (ffmpeg
in production, a pure stand-in in tests) returns the finished file blobs and per-chunk
timings; the stage turns the timings into the provenance map, and the CLI writes both.
Keeping ffmpeg behind this port is what lets the stage stay free of subprocess/file I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from thesis_audiobook.config import OutputMode
from thesis_audiobook.ir import StrictModel


class ChapterSpec(StrictModel):
    index: int
    title: str
    chunk_ids: list[str]


class AudiobookPlan(StrictModel):
    title: str
    author: str | None = None
    narrator: str
    slug: str
    output_mode: OutputMode = "m4b"
    chapters: list[ChapterSpec] = []


class ChunkTiming(StrictModel):
    chunk_id: str
    seconds: float


@dataclass(frozen=True)
class NamedBlob:
    """One output file held in memory; the CLI composition root writes it to disk."""

    filename: str
    data: bytes


@dataclass(frozen=True)
class MuxResult:
    outputs: list[NamedBlob]
    timings: list[ChunkTiming]
    chapter_count: int


class AudioMuxer(Protocol):
    def mux(self, plan: AudiobookPlan, audio: dict[str, bytes]) -> MuxResult: ...
