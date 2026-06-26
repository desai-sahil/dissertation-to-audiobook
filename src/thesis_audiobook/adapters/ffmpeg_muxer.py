"""Real AudioMuxer over the ffmpeg/ffprobe binaries.

Concatenates rendered chunk audio into either one M4B with chapter markers and
metadata, or one MP3 per chapter. Requires ffmpeg and ffprobe on PATH; the sandbox
and CI have neither, so this adapter is never exercised offline (the pipeline uses
MockMuxer there). It is what the user's local `--preview` / full render invokes, so it
is written to work end-to-end but verified on the user's machine.
"""
# Subprocess plumbing against external binaries; exercised only on a host with ffmpeg.
# pragma: no cover

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from thesis_audiobook.ports.audio import (
    AudiobookPlan,
    ChapterSpec,
    ChunkTiming,
    MuxResult,
    NamedBlob,
)


class FfmpegUnavailableError(RuntimeError):
    """ffmpeg or ffprobe is not installed or not on PATH."""


def escape_ffmetadata(value: str) -> str:
    """Backslash-escape the FFMETADATA1 special characters in a key or value.

    Pure and offline-testable, unlike the rest of this adapter. Without it a chapter
    title containing '=' or ';' (e.g. 'Results; pH = 7') would corrupt the metadata.
    """
    for char in ("\\", "=", ";", "#"):
        value = value.replace(char, "\\" + char)
    return value.replace("\n", "\\\n")


class FfmpegMuxer:  # pragma: no cover - requires the ffmpeg/ffprobe binaries
    def __init__(
        self,
        *,
        ffmpeg: str = "ffmpeg",
        ffprobe: str = "ffprobe",
        bitrate: str = "128k",
        chunk_ext: str = "mp3",
    ) -> None:
        self._ffmpeg = ffmpeg
        self._ffprobe = ffprobe
        self._bitrate = bitrate
        self._chunk_ext = chunk_ext

    def mux(self, plan: AudiobookPlan, audio: dict[str, bytes]) -> MuxResult:
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            paths = self._write_chunks(audio, tmpdir)
            timings = self._probe_timings(plan, paths)
            durations = {t.chunk_id: t.seconds for t in timings}
            if plan.output_mode == "mp3":
                outputs = [
                    self._encode_chapter_mp3(plan, chapter, paths, tmpdir)
                    for chapter in plan.chapters
                ]
            else:
                outputs = [self._encode_m4b(plan, paths, durations, tmpdir)]
        return MuxResult(outputs=outputs, timings=timings, chapter_count=len(plan.chapters))

    def _require_tools(self) -> None:
        missing = [t for t in (self._ffmpeg, self._ffprobe) if shutil.which(t) is None]
        if missing:
            raise FfmpegUnavailableError(
                f"{' and '.join(missing)} not found on PATH (try: brew install ffmpeg)"
            )

    def _write_chunks(self, audio: dict[str, bytes], tmpdir: Path) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for chunk_id, data in audio.items():
            path = tmpdir / f"{chunk_id}.{self._chunk_ext}"
            path.write_bytes(data)
            paths[chunk_id] = path
        return paths

    def _probe_timings(self, plan: AudiobookPlan, paths: dict[str, Path]) -> list[ChunkTiming]:
        timings: list[ChunkTiming] = []
        for chapter in plan.chapters:
            for chunk_id in chapter.chunk_ids:
                seconds = self._probe(paths[chunk_id]) if chunk_id in paths else 0.0
                timings.append(ChunkTiming(chunk_id=chunk_id, seconds=seconds))
        return timings

    def _probe(self, path: Path) -> float:
        out = subprocess.run(
            [self._ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True,
            check=True,
            text=True,
        )
        return float(json.loads(out.stdout)["format"]["duration"])

    def _concat_list(self, chunk_ids: list[str], paths: dict[str, Path], tmpdir: Path) -> Path:
        list_path = tmpdir / f"concat_{abs(hash(tuple(chunk_ids)))}.txt"
        lines = [f"file '{paths[cid].as_posix()}'" for cid in chunk_ids if cid in paths]
        list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return list_path

    def _encode_chapter_mp3(
        self, plan: AudiobookPlan, chapter: ChapterSpec, paths: dict[str, Path], tmpdir: Path
    ) -> NamedBlob:
        list_path = self._concat_list(chapter.chunk_ids, paths, tmpdir)
        out_path = tmpdir / f"{plan.slug}.ch{chapter.index:02d}.mp3"
        subprocess.run(
            [
                self._ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c:a",
                "libmp3lame",
                "-b:a",
                self._bitrate,
                "-metadata",
                f"title={chapter.title}",
                "-metadata",
                f"album={plan.title}",
                "-metadata",
                f"artist={plan.author or ''}",
                "-metadata",
                f"track={chapter.index}",
                str(out_path),
            ],
            capture_output=True,
            check=True,
        )
        return NamedBlob(filename=out_path.name, data=out_path.read_bytes())

    def _encode_m4b(
        self,
        plan: AudiobookPlan,
        paths: dict[str, Path],
        durations: dict[str, float],
        tmpdir: Path,
    ) -> NamedBlob:
        ordered = [cid for chapter in plan.chapters for cid in chapter.chunk_ids]
        list_path = self._concat_list(ordered, paths, tmpdir)
        meta_path = self._ffmetadata(plan, durations, tmpdir)
        # m4b and mp4 are the same AAC/MP4 container; only the extension differs.
        out_path = tmpdir / f"{plan.slug}.{plan.output_mode}"
        subprocess.run(
            [
                self._ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-i",
                str(meta_path),
                "-map",
                "0:a",
                "-map_metadata",
                "1",
                "-c:a",
                "aac",
                "-b:a",
                self._bitrate,
                "-metadata",
                f"title={plan.title}",
                "-metadata",
                f"album={plan.title}",
                "-metadata",
                f"artist={plan.author or ''}",
                "-metadata",
                f"composer={plan.narrator}",
                str(out_path),
            ],
            capture_output=True,
            check=True,
        )
        return NamedBlob(filename=out_path.name, data=out_path.read_bytes())

    def _ffmetadata(self, plan: AudiobookPlan, durations: dict[str, float], tmpdir: Path) -> Path:
        lines = [";FFMETADATA1"]
        cursor_ms = 0
        for chapter in plan.chapters:
            start_ms = cursor_ms
            span_ms = int(round(sum(durations.get(cid, 0.0) for cid in chapter.chunk_ids) * 1000))
            end_ms = start_ms + span_ms
            lines += [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={escape_ffmetadata(chapter.title)}",
            ]
            cursor_ms = end_ms
        meta_path = tmpdir / "chapters.ffmeta"
        meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return meta_path
