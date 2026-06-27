"""Composition helpers: build a Context wired with mock adapters.

Used by the CLI and by tests so the whole pipeline runs offline. Real adapters are
wired in later milestones behind the same ports.
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path

from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
from thesis_audiobook.adapters.elevenlabs_tts import ElevenLabsClient, ElevenLabsPronunciation
from thesis_audiobook.adapters.ffmpeg_muxer import FfmpegMuxer
from thesis_audiobook.adapters.file_cache import FileCache
from thesis_audiobook.adapters.grobid_client import GrobidClient
from thesis_audiobook.adapters.markdown_bib_parser import MarkdownBibParser
from thesis_audiobook.adapters.markdown_parser import MarkdownFileParser
from thesis_audiobook.adapters.marker_parser import MarkerParser
from thesis_audiobook.adapters.mineru_parser import MinerUParser
from thesis_audiobook.adapters.mocks import (
    MemoryCache,
    MockBibParser,
    MockLlm,
    MockMuxer,
    MockParser,
    MockPronunciation,
    MockTts,
)
from thesis_audiobook.adapters.poppler_parser import PopplerBibParser, PopplerParser
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context
from thesis_audiobook.log import StructuredLogger
from thesis_audiobook.ports.bib import BibParser
from thesis_audiobook.ports.parser import PdfParser
from thesis_audiobook.pronunciation import PronunciationLexicon
from thesis_audiobook.warnings import WarningsSink


def load_pronunciation_lexicon() -> PronunciationLexicon:
    """Read and validate the versioned domain pronunciation dictionary (package data)."""
    data = (
        importlib.resources.files("thesis_audiobook")
        .joinpath("data/pronunciation.json")
        .read_text(encoding="utf-8")
    )
    return PronunciationLexicon.model_validate_json(data)


def _elevenlabs_api_key() -> str | None:
    return os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_LABS_API_KEY")


def build_mock_context(
    config: Config,
    *,
    pdf_bytes: bytes,
    mock_ir: Path | str,
    log_enabled: bool = True,
) -> Context:
    return Context(
        config=config,
        parser=MockParser(mock_ir),
        bib=MockBibParser(),
        llm=MockLlm(),
        tts=MockTts(),
        cache=MemoryCache(),
        muxer=MockMuxer(),
        pronunciation=MockPronunciation(),
        log=StructuredLogger(enabled=log_enabled),
        warnings=WarningsSink(),
        pronunciation_lexicon=load_pronunciation_lexicon(),
        pdf_bytes=pdf_bytes,
    )


def select_parser_adapters(config: Config) -> tuple[PdfParser, BibParser]:
    """Pick the real parser + bibliography adapters for the configured backend.

    Poppler is fully local; Marker/MinerU pair with GROBID for citation linkage. The
    "markdown" backend ingests a pre-parsed markdown file (from a standalone Marker run),
    with no separate bibliography source. LLM and TTS are wired separately.
    """
    if config.parser_backend == "markdown":
        if not config.markdown_path:
            raise ValueError("parser_backend 'markdown' requires config.markdown_path")
        return MarkdownFileParser(config.markdown_path), MarkdownBibParser(config.markdown_path)
    if config.parser_backend == "poppler":
        return PopplerParser(), PopplerBibParser()
    if config.parser_backend == "mineru":
        return MinerUParser(), GrobidClient(config.grobid_url)
    return MarkerParser(), GrobidClient(config.grobid_url)


def build_context(
    config: Config,
    *,
    pdf_bytes: bytes,
    log_enabled: bool = True,
    use_real_llm: bool = False,
    use_real_tts: bool = False,
) -> Context:
    """Context wired with real parser/bib adapters and a persistent FileCache.

    The LLM and TTS stay mocked by default so runs are offline and free. Pass
    ``use_real_llm=True`` (CLI ``--llm anthropic``) for real glosses, and
    ``use_real_tts=True`` (CLI ``--tts elevenlabs``) for the real ElevenLabs render +
    pronunciation publish + ffmpeg M4B mux. Both real paths cost money and need their
    API keys; the real render also needs ffmpeg on PATH.
    """
    parser, bib = select_parser_adapters(config)
    api_key = _elevenlabs_api_key()
    return Context(
        config=config,
        parser=parser,
        bib=bib,
        llm=AnthropicClient() if use_real_llm else MockLlm(),
        tts=ElevenLabsClient(api_key=api_key) if use_real_tts else MockTts(),
        cache=FileCache(config.cache_dir),
        muxer=FfmpegMuxer() if use_real_tts else MockMuxer(),
        pronunciation=(
            ElevenLabsPronunciation(api_key=api_key) if use_real_tts else MockPronunciation()
        ),
        log=StructuredLogger(enabled=log_enabled),
        warnings=WarningsSink(),
        pronunciation_lexicon=load_pronunciation_lexicon(),
        pdf_bytes=pdf_bytes,
    )
