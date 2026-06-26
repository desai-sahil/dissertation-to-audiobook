"""Deterministic mock adapters. Never network, never spend money.

These let the entire pipeline run offline, fast, and free in tests and in the M0
walking skeleton.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from thesis_audiobook.audio import silent_wav, wav_duration
from thesis_audiobook.ir import Document
from thesis_audiobook.ports.audio import AudiobookPlan, ChunkTiming, MuxResult, NamedBlob
from thesis_audiobook.ports.bib import BibResult
from thesis_audiobook.ports.tts import TtsRequest
from thesis_audiobook.pronunciation import (
    DictionaryLocator,
    PronunciationRule,
    rules_to_api_payload,
)


class MockParser:
    """Returns a fixed parse loaded from a canned IR JSON file.

    Ignores the PDF bytes entirely; real Marker/MinerU parsing lands in M2.
    """

    def __init__(self, ir_path: Path | str) -> None:
        self._ir_path = Path(ir_path)

    def parse(self, pdf_bytes: bytes) -> Document:
        return Document.model_validate_json(self._ir_path.read_text(encoding="utf-8"))


class MockBibParser:
    """Returns an empty bibliography. Real GROBID linkage lands in M2."""

    def parse(self, pdf_bytes: bytes) -> BibResult:
        return BibResult(bibliography={}, citations={})


class MockLlm:
    """Canned, deterministic LLM output keyed by a hash of the input. Never networks.

    Keying by input hash makes gloss/summary tests reproducible: identical input IR
    plus identical prompt yields byte-identical spoken output.
    """

    def complete(self, prompt: str) -> str:
        # Letters-only token: deterministic per prompt, and free of digits/notation so
        # it survives the normalizer unchanged (like a real, clean gloss would).
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        token = "".join(c for c in digest if c.isalpha())[:8]
        return f"a mock gloss for input {token}"


class MockTts:
    """Returns a deterministic silent WAV sized from len(text). Never networks."""

    def synthesize(self, req: TtsRequest) -> bytes:
        return silent_wav(seconds=len(req.text) / 15.0)


class MockPronunciation:
    """Returns a deterministic locator keyed by the rules. Never networks."""

    def publish(self, name: str, rules: list[PronunciationRule]) -> DictionaryLocator:
        payload = json.dumps(
            {"name": name, "rules": rules_to_api_payload(rules)}, sort_keys=True, ensure_ascii=False
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return DictionaryLocator(
            pronunciation_dictionary_id=f"mock-dict-{digest[:8]}",
            version_id=f"mock-ver-{digest[8:16]}",
        )


class MockMuxer:
    """Pure stand-in muxer: no ffmpeg. Times chunks via wav_duration and concatenates
    their WAV bytes into a deterministic placeholder file (one M4B, or one MP3 per
    chapter). Not a real MP4 container; the real one is built by FfmpegMuxer on a
    machine with ffmpeg. This is what keeps the whole pipeline runnable offline.
    """

    def mux(self, plan: AudiobookPlan, audio: dict[str, bytes]) -> MuxResult:
        ordered = [(ch, cid) for ch in plan.chapters for cid in ch.chunk_ids]
        timings = [
            ChunkTiming(
                chunk_id=cid,
                seconds=wav_duration(audio[cid]) if audio.get(cid) else 0.0,
            )
            for _, cid in ordered
        ]
        if plan.output_mode == "mp3":
            outputs = [
                NamedBlob(
                    filename=f"{plan.slug}.ch{ch.index:02d}.mp3",
                    data=b"".join(audio.get(cid, b"") for cid in ch.chunk_ids),
                )
                for ch in plan.chapters
            ]
        else:
            outputs = [
                NamedBlob(
                    filename=f"{plan.slug}.{plan.output_mode}",
                    data=b"".join(audio.get(cid, b"") for _, cid in ordered),
                )
            ]
        return MuxResult(outputs=outputs, timings=timings, chapter_count=len(plan.chapters))


class MemoryCache:
    """In-memory content-addressed store."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def put(self, key: str, value: bytes) -> None:
        self._store[key] = value
