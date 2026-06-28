from __future__ import annotations

from pathlib import Path

from thesis_audiobook.audio import silent_wav
from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.chunking import plan_chunks_from_text
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Chunk, Document, DocumentMeta
from thesis_audiobook.ports.tts import TtsRequest
from thesis_audiobook.stages.tts import TtsStage


class RecordingTts:
    """Records every request and returns deterministic silent audio. Never networks."""

    cache_tag = "mock"

    def __init__(self) -> None:
        self.requests: list[TtsRequest] = []

    def synthesize(self, req: TtsRequest) -> bytes:
        self.requests.append(req)
        return silent_wav(seconds=len(req.text) / 15.0)


def _chunks(n: int) -> list[Chunk]:
    chunks = [
        Chunk(id=f"chunk.{i + 1}", text=f"Sentence number {i + 1}.", chapter=1) for i in range(n)
    ]
    for i, chunk in enumerate(chunks):
        chunk.prev_id = chunks[i - 1].id if i > 0 else None
        chunk.next_id = chunks[i + 1].id if i + 1 < len(chunks) else None
    return chunks


def _ctx(tiny_ir_path: Path, tts: RecordingTts) -> Context:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ctx.tts = tts
    return ctx


def test_chunks_stay_under_limit_and_conserve_text() -> None:
    text = "This is a sentence that repeats. " * 80
    chunks = plan_chunks_from_text(text, limit=150)
    assert all(len(chunk.text) <= 150 for chunk in chunks)
    assert "".join(chunk.text for chunk in chunks) == text  # conservation
    assert chunks[0].prev_id is None and chunks[-1].next_id is None


def test_neighbor_text_is_passed_through(tiny_ir_path: Path) -> None:
    tts = RecordingTts()
    doc = Document(meta=DocumentMeta(title="t"), chunks=_chunks(3))
    TtsStage().run(doc, _ctx(tiny_ir_path, tts))

    by_text = {req.text: req for req in tts.requests}
    middle = by_text["Sentence number 2."]
    assert middle.previous_text == "Sentence number 1."
    assert middle.next_text == "Sentence number 3."
    assert by_text["Sentence number 1."].previous_text is None
    assert by_text["Sentence number 3."].next_text is None
    # The renderer stitches via neighbor TEXT only; request-id stitching stays empty, so
    # leaving the request-id lists out of the cache key is safe (see chunk_cache_key).
    assert all(not req.previous_request_ids and not req.next_request_ids for req in tts.requests)


def test_unchanged_chunks_hit_cache_and_edited_chunk_plus_seams_re_render(
    tiny_ir_path: Path,
) -> None:
    tts = RecordingTts()
    ctx = _ctx(tiny_ir_path, tts)
    doc = Document(meta=DocumentMeta(title="t"), chunks=_chunks(5))

    TtsStage().run(doc, ctx)
    assert len(tts.requests) == 5  # cold render

    # Re-run against the same cache: every chunk is a hit, no new synth calls.
    ctx.rendered = {}
    TtsStage().run(doc, ctx)
    assert len(tts.requests) == 5

    # Edit the middle block. Its own key changes, and because neighbors are in the key
    # (spec section 10), the two adjacent seams refresh too: 3 re-renders, 2 served free.
    ctx.rendered = {}
    doc.chunks[2].text = "An edited sentence."
    TtsStage().run(doc, ctx)
    assert len(tts.requests) == 5 + 3
