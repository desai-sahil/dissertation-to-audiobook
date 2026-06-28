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


class MockLlm:
    """Canned, deterministic LLM output keyed by a hash of the input. Never networks.

    Keying by input hash makes gloss/summary tests reproducible: identical input IR
    plus identical prompt yields byte-identical spoken output.
    """

    def complete(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> str:
        # Letters-only token: deterministic per prompt, and free of digits/notation so
        # it survives the normalizer unchanged (like a real, clean gloss would). The
        # system/max_tokens overrides are ignored: the canned reply is never valid JSON,
        # so the structured stages parse it to an empty result and no-op offline.
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
    """Pure stand-in muxer: no ffmpeg. Times chunks via wav_duration and concatenates their
    WAV bytes into deterministic placeholder files matching the real output SET: a chaptered
    file (.mp4/.m4b) for those modes, plus a single whole-book .mp3 every render. Not real
    containers and the cover is ignored here; FfmpegMuxer builds the real cover-video / album
    art on a machine with ffmpeg. This keeps the whole pipeline runnable offline.
    """

    def mux(
        self, plan: AudiobookPlan, audio: dict[str, bytes], cover: bytes | None = None
    ) -> MuxResult:
        ordered = [cid for chapter in plan.chapters for cid in chapter.chunk_ids]
        timings = [
            ChunkTiming(chunk_id=cid, seconds=wav_duration(audio[cid]) if audio.get(cid) else 0.0)
            for cid in ordered
        ]
        whole = b"".join(audio.get(cid, b"") for cid in ordered)
        outputs: list[NamedBlob] = []
        if plan.output_mode in ("mp4", "m4b"):
            outputs.append(NamedBlob(filename=f"{plan.slug}.{plan.output_mode}", data=whole))
        outputs.append(NamedBlob(filename=f"{plan.slug}.mp3", data=whole))
        return MuxResult(outputs=outputs, timings=timings, chapter_count=len(plan.chapters))


class MemoryCache:
    """In-memory content-addressed store."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def put(self, key: str, value: bytes) -> None:
        self._store[key] = value
