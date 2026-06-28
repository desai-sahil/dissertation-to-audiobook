from __future__ import annotations

from pathlib import Path

from thesis_audiobook.audio import silent_wav
from thesis_audiobook.bootstrap import build_mock_context, load_pronunciation_lexicon
from thesis_audiobook.config import Config
from thesis_audiobook.ir import Chunk, Document, DocumentMeta
from thesis_audiobook.ports.tts import TtsRequest
from thesis_audiobook.pronunciation import PronunciationPublishError, PronunciationRule
from thesis_audiobook.stages.lexicon import LexiconStage
from thesis_audiobook.stages.tts import TtsStage


class _Recorder:
    cache_tag = "mock"

    def __init__(self) -> None:
        self.requests: list[TtsRequest] = []

    def synthesize(self, req: TtsRequest) -> bytes:
        self.requests.append(req)
        return silent_wav(seconds=len(req.text) / 15.0)


def test_pronunciation_file_is_slim_pronunciation_aids_only() -> None:
    lexicon = load_pronunciation_lexicon()
    assert lexicon.version  # versioned, source-controlled
    aliases = {rule.string_to_replace for rule in lexicon.rules if rule.type == "alias"}
    # Plain-English terms are normalizer territory, not pronunciation aids - dropped.
    assert {"gs", "goxz", "ABA", "WT"}.isdisjoint(aliases)
    # Genuine voice-manglers (gene names) plus the Greek phoneme remain.
    assert {"NADPH", "ABI1"} <= aliases
    assert any(rule.type == "phoneme" for rule in lexicon.rules)


def test_lexicon_stage_publishes_and_records_locator(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    LexiconStage().run(Document(meta=DocumentMeta(title="t")), ctx)
    assert len(ctx.dictionary_locators) == 1
    locator = ctx.dictionary_locators[0]
    assert locator.pronunciation_dictionary_id.startswith("mock-dict-")
    assert locator.version_id.startswith("mock-ver-")


def test_locator_is_attached_to_every_render(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    recorder = _Recorder()
    ctx.tts = recorder
    doc = Document(
        meta=DocumentMeta(title="t"),
        chunks=[Chunk(id="chunk.1", text="Stomatal conductance fell.", chapter=1)],
    )
    LexiconStage().run(doc, ctx)
    TtsStage().run(doc, ctx)
    assert recorder.requests[0].locators == ctx.dictionary_locators
    assert recorder.requests[0].locators  # non-empty


class _FailingPublisher:
    def publish(self, name: str, rules: list[PronunciationRule]) -> object:
        raise PronunciationPublishError("missing_permissions")


def test_publish_failure_warns_and_renders_without_dictionary(tiny_ir_path: Path) -> None:
    ctx = build_mock_context(Config(), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    ctx.pronunciation = _FailingPublisher()  # type: ignore[assignment]
    # The optional dictionary publish must not abort the run.
    LexiconStage().run(Document(meta=DocumentMeta(title="t")), ctx)
    assert ctx.dictionary_locators == []
    assert any("publish skipped" in warning.reason for warning in ctx.warnings.items)
