"""Real AudioMuxer over the ffmpeg/ffprobe binaries.

Concatenates rendered chunk audio into the deliverable set. For an mp4/m4b render that
is a chaptered container (mp4 = a still-cover video so the art shows the whole time it
plays; m4b = AAC audiobook with embedded cover art) PLUS a single whole-book .mp3 with
the cover as ID3 album art. For an mp3 render it is just that one whole-book .mp3. When
no cover is supplied every image step is skipped and the outputs are audio-only.

Requires ffmpeg and ffprobe on PATH; the sandbox and CI have neither, so this adapter is
never exercised offline (the pipeline uses MockMuxer there). It is what the user's local
`--preview` / full render invokes, so it is written to work end-to-end but verified on
the user's machine.
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

    def mux(
        self, plan: AudiobookPlan, audio: dict[str, bytes], cover: bytes | None = None
    ) -> MuxResult:
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            paths = self._write_chunks(audio, tmpdir)
            timings = self._probe_timings(plan, paths)
            durations = {t.chunk_id: t.seconds for t in timings}
            cover_path = self._write_cover(cover, tmpdir)
            outputs: list[NamedBlob] = []
            if plan.output_mode == "mp4":
                outputs.append(self._encode_mp4(plan, paths, durations, tmpdir, cover_path))
            elif plan.output_mode == "m4b":
                outputs.append(self._encode_m4b(plan, paths, durations, tmpdir, cover_path))
            # A single whole-book MP3 (cover as album art) accompanies every render.
            outputs.append(self._encode_whole_mp3(plan, paths, tmpdir, cover_path))
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

    def _write_cover(self, cover: bytes | None, tmpdir: Path) -> Path | None:
        if not cover:
            return None
        path = tmpdir / "cover.png"
        path.write_bytes(cover)
        return path

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

    def _ordered_ids(self, plan: AudiobookPlan) -> list[str]:
        return [cid for chapter in plan.chapters for cid in chapter.chunk_ids]

    def _concat_list(self, chunk_ids: list[str], paths: dict[str, Path], tmpdir: Path) -> Path:
        list_path = tmpdir / f"concat_{abs(hash(tuple(chunk_ids)))}.txt"
        lines = [f"file '{paths[cid].as_posix()}'" for cid in chunk_ids if cid in paths]
        list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return list_path

    def _run(self, args: list[str]) -> None:
        subprocess.run([self._ffmpeg, "-y", *args], capture_output=True, check=True)

    def _book_metadata(self, plan: AudiobookPlan) -> list[str]:
        return [
            "-metadata",
            f"title={plan.title}",
            "-metadata",
            f"album={plan.title}",
            "-metadata",
            f"artist={plan.author or ''}",
            "-metadata",
            f"composer={plan.narrator}",
        ]

    def _encode_mp4(
        self,
        plan: AudiobookPlan,
        paths: dict[str, Path],
        durations: dict[str, float],
        tmpdir: Path,
        cover_path: Path | None,
    ) -> NamedBlob:
        """mp4 with chapters. With a cover the still image becomes a full-frame video that
        shows for the whole runtime; without one it is an audio-only mp4."""
        list_path = self._concat_list(self._ordered_ids(plan), paths, tmpdir)
        meta_path = self._ffmetadata(plan, durations, tmpdir)
        out_path = tmpdir / f"{plan.slug}.mp4"
        if cover_path is not None:
            # inputs: 0=looped cover image, 1=concatenated audio, 2=chapter metadata.
            self._run(
                [
                    "-loop",
                    "1",
                    "-framerate",
                    "2",
                    "-i",
                    str(cover_path),
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-i",
                    str(meta_path),
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-map_metadata",
                    "2",
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    "2",
                    # x264/yuv420p needs even dimensions; round the cover down to even.
                    "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:a",
                    "aac",
                    "-b:a",
                    self._bitrate,
                    "-shortest",
                    *self._book_metadata(plan),
                    str(out_path),
                ]
            )
        else:
            # inputs: 0=concatenated audio, 1=chapter metadata.
            self._run(
                [
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
                    *self._book_metadata(plan),
                    str(out_path),
                ]
            )
        return NamedBlob(filename=out_path.name, data=out_path.read_bytes())

    def _encode_m4b(
        self,
        plan: AudiobookPlan,
        paths: dict[str, Path],
        durations: dict[str, float],
        tmpdir: Path,
        cover_path: Path | None,
    ) -> NamedBlob:
        """m4b audiobook (AAC + chapters). A cover is embedded as attached-pic album art
        that audiobook players show on the now-playing screen."""
        list_path = self._concat_list(self._ordered_ids(plan), paths, tmpdir)
        meta_path = self._ffmetadata(plan, durations, tmpdir)
        out_path = tmpdir / f"{plan.slug}.m4b"
        if cover_path is not None:
            # inputs: 0=concatenated audio, 1=chapter metadata, 2=cover image.
            self._run(
                [
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-i",
                    str(meta_path),
                    "-i",
                    str(cover_path),
                    "-map",
                    "0:a",
                    "-map",
                    "2:v",
                    "-map_metadata",
                    "1",
                    "-c:a",
                    "aac",
                    "-b:a",
                    self._bitrate,
                    "-c:v",
                    "mjpeg",
                    "-disposition:v",
                    "attached_pic",
                    *self._book_metadata(plan),
                    str(out_path),
                ]
            )
        else:
            # inputs: 0=concatenated audio, 1=chapter metadata.
            self._run(
                [
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
                    *self._book_metadata(plan),
                    str(out_path),
                ]
            )
        return NamedBlob(filename=out_path.name, data=out_path.read_bytes())

    def _encode_whole_mp3(
        self,
        plan: AudiobookPlan,
        paths: dict[str, Path],
        tmpdir: Path,
        cover_path: Path | None,
    ) -> NamedBlob:
        """One whole-book MP3. A cover rides along as an ID3 attached-picture album art."""
        list_path = self._concat_list(self._ordered_ids(plan), paths, tmpdir)
        out_path = tmpdir / f"{plan.slug}.mp3"
        if cover_path is not None:
            # inputs: 0=concatenated audio, 1=cover image.
            self._run(
                [
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-i",
                    str(cover_path),
                    "-map",
                    "0:a",
                    "-map",
                    "1:v",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    self._bitrate,
                    # Transcode the cover to JPEG: an ID3 APIC frame with a copied PNG is
                    # valid but many players won't render it, so match the m4b path.
                    "-c:v",
                    "mjpeg",
                    "-id3v2_version",
                    "3",
                    "-metadata:s:v",
                    "title=Album cover",
                    "-metadata:s:v",
                    "comment=Cover (front)",
                    "-disposition:v",
                    "attached_pic",
                    *self._book_metadata(plan),
                    str(out_path),
                ]
            )
        else:
            self._run(
                [
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
                    *self._book_metadata(plan),
                    str(out_path),
                ]
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
