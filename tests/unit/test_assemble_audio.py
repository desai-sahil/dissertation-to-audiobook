from __future__ import annotations

from pathlib import Path

from thesis_audiobook.adapters.ffmpeg_muxer import escape_ffmetadata
from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Chunk, Document, DocumentMeta
from thesis_audiobook.provenance import ProvenanceMap, block_ids_at
from thesis_audiobook.stages import build_default_pipeline
from thesis_audiobook.stages.assemble_audio import AssembleAudioStage, build_audiobook_plan
from thesis_audiobook.stages.tts import TtsStage


def _two_chapter_doc() -> Document:
    blocks = [
        Block(id="h1", type=BlockType.heading, chapter=1, text="Introduction"),
        Block(id="h2", type=BlockType.heading, chapter=2, text="Results"),
    ]
    chunks = [
        Chunk(id="chunk.1", text="Intro one.", chapter=1, block_ids=["b1"]),
        Chunk(id="chunk.2", text="Intro two.", chapter=1, block_ids=["b2"]),
        Chunk(id="chunk.3", text="Results one.", chapter=2, block_ids=["b3"]),
    ]
    for i, chunk in enumerate(chunks):
        chunk.prev_id = chunks[i - 1].id if i > 0 else None
        chunk.next_id = chunks[i + 1].id if i + 1 < len(chunks) else None
    return Document(
        meta=DocumentMeta(title="Demo Thesis", author="A. Author"), blocks=blocks, chunks=chunks
    )


def _ctx(config: Config, tiny_ir_path: Path) -> Context:
    return build_mock_context(config, pdf_bytes=b"x", mock_ir=tiny_ir_path)


def test_plan_has_one_chapter_per_chapter_with_titles(tiny_ir_path: Path) -> None:
    doc = _two_chapter_doc()
    plan = build_audiobook_plan(doc, _ctx(Config(), tiny_ir_path))
    assert [chapter.index for chapter in plan.chapters] == [1, 2]
    assert plan.chapters[0].title == "Introduction"
    assert plan.chapters[1].title == "Results"
    assert plan.chapters[0].chunk_ids == ["chunk.1", "chunk.2"]
    assert plan.chapters[1].chunk_ids == ["chunk.3"]
    assert plan.author == "A. Author"


def test_assemble_emits_m4b_plus_whole_book_mp3_with_provenance(tiny_ir_path: Path) -> None:
    doc = _two_chapter_doc()
    ctx = _ctx(Config(), tiny_ir_path)
    TtsStage().run(doc, ctx)
    AssembleAudioStage().run(doc, ctx)

    assert ctx.chapter_count == 2
    # m4b mode: the chaptered .m4b plus a single whole-book .mp3 alongside.
    assert [Path(blob.filename).suffix for blob in ctx.audio_outputs] == [".m4b", ".mp3"]
    # The primary deliverable (final_audio) is the chaptered file, not the mp3.
    assert ctx.final_audio == ctx.audio_outputs[0].data

    prov = ctx.provenance
    assert prov is not None
    # Round-trips byte-for-byte through JSON.
    assert ProvenanceMap.model_validate_json(prov.model_dump_json()) == prov
    # Timeline is gapless and maps back to the source block ids.
    assert [seg.block_ids for seg in prov.segments] == [["b1"], ["b2"], ["b3"]]
    assert prov.segments[0].start_seconds == 0.0
    assert prov.segments[1].start_seconds == prov.segments[0].end_seconds
    assert block_ids_at(prov, prov.segments[1].start_seconds + 0.0001) == ["b2"]


def test_mp3_mode_emits_single_whole_book_file(tiny_ir_path: Path) -> None:
    doc = _two_chapter_doc()
    ctx = _ctx(Config(output_mode="mp3"), tiny_ir_path)
    TtsStage().run(doc, ctx)
    AssembleAudioStage().run(doc, ctx)

    # mp3 mode is the single whole-book file only (no chaptered container alongside).
    assert len(ctx.audio_outputs) == 1
    assert ctx.audio_outputs[0].filename.endswith(".mp3")


def test_mp4_mode_emits_chaptered_mp4_plus_whole_book_mp3(tiny_ir_path: Path) -> None:
    doc = _two_chapter_doc()
    ctx = _ctx(Config(output_mode="mp4"), tiny_ir_path)
    TtsStage().run(doc, ctx)
    AssembleAudioStage().run(doc, ctx)

    assert [Path(blob.filename).suffix for blob in ctx.audio_outputs] == [".mp4", ".mp3"]
    assert ctx.chapter_count == 2


def test_assemble_passes_cover_image_through_to_muxer(tiny_ir_path: Path) -> None:
    # The stage must forward ctx.cover_image to the muxer port; a spy captures it.
    doc = _two_chapter_doc()
    ctx = _ctx(Config(output_mode="mp4"), tiny_ir_path)
    TtsStage().run(doc, ctx)
    ctx.cover_image = b"\x89PNG fake-cover-bytes"

    captured: dict[str, bytes | None] = {}
    real_muxer = ctx.muxer

    class SpyMuxer:
        def mux(
            self,
            plan: object,
            audio: dict[str, bytes],
            cover: bytes | None = None,
        ) -> object:
            captured["cover"] = cover
            return real_muxer.mux(plan, audio, cover=cover)  # type: ignore[arg-type]

    ctx.muxer = SpyMuxer()  # type: ignore[assignment]
    AssembleAudioStage().run(doc, ctx)

    assert captured["cover"] == b"\x89PNG fake-cover-bytes"


def test_real_script_front_matter_folds_into_chapters_no_spurious_markers(
    tiny_ir_path: Path,
) -> None:
    # Runs the REAL assemble_script stage, which brackets the body with chapter=None
    # intro/outro chunks; a small limit forces them into their own chunks. The plan must
    # fold them into real chapters: no "Front matter" markers, contiguous 1..N indices.
    ctx = _ctx(Config(chunk_char_limit=200), tiny_ir_path)
    doc = build_default_pipeline().run(
        Document(meta=DocumentMeta(title="x")), ctx, to="assemble_script"
    )
    assert any(chunk.chapter is None for chunk in doc.chunks)  # precondition

    plan = build_audiobook_plan(doc, ctx)
    assert "Front matter" not in [chapter.title for chapter in plan.chapters]
    assert [chapter.index for chapter in plan.chapters] == list(range(1, len(plan.chapters) + 1))
    # Leading intro chunk is folded into the first chapter, and every chunk is assigned
    # to exactly one chapter, in reading order (conservation).
    assert plan.chapters[0].chunk_ids[0] == doc.chunks[0].id
    assigned = [cid for chapter in plan.chapters for cid in chapter.chunk_ids]
    assert assigned == [chunk.id for chunk in doc.chunks]


def test_escape_ffmetadata_escapes_specials() -> None:
    assert escape_ffmetadata("Results; pH = 7 #1") == "Results\\; pH \\= 7 \\#1"
    assert escape_ffmetadata("a\\b") == "a\\\\b"
