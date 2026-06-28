"""Shared fixtures and the autouse cost/network guard.

No non-live test may reach ElevenLabs or the LLM. The guard patches the real
adapters' entry methods so any accidental call raises.
"""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import pytest

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config
from thesis_audiobook.context import Context

REPO_ROOT = Path(__file__).resolve().parents[1]
TINY_IR = REPO_ROOT / "tests" / "fixtures" / "tiny.ir.json"


@pytest.fixture(autouse=True)
def _no_live_calls(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("live") is not None:
        return  # opt-in live tests may proceed
    if request.node.get_closest_marker("contract") is not None:
        return  # offline contract tests inject a fake SDK client; they never network

    def boom(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("live external call in a non-live test")

    monkeypatch.setattr(
        "thesis_audiobook.adapters.elevenlabs_tts.ElevenLabsClient.synthesize", boom
    )
    monkeypatch.setattr(
        "thesis_audiobook.adapters.elevenlabs_tts.ElevenLabsPronunciation.publish", boom
    )
    monkeypatch.setattr("thesis_audiobook.adapters.anthropic_llm.AnthropicClient.complete", boom)
    monkeypatch.setattr("thesis_audiobook.adapters.anthropic_llm.AnthropicClient.describe", boom)


@pytest.fixture
def tiny_ir_path() -> Path:
    return TINY_IR


@pytest.fixture
def sample_pdf() -> Path:
    return REPO_ROOT / "sample" / "Chapter6_preview.pdf"


@pytest.fixture
def cassette_dir() -> Path:
    return REPO_ROOT / "tests" / "fixtures" / "cassettes"


@pytest.fixture
def golden_dir() -> Path:
    return REPO_ROOT / "tests" / "fixtures" / "golden"


@pytest.fixture
def mock_context(tiny_ir_path: Path) -> Context:
    return build_mock_context(Config(), pdf_bytes=b"%PDF-mock", mock_ir=tiny_ir_path)
