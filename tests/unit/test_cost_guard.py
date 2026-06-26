from __future__ import annotations

import pytest

from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
from thesis_audiobook.adapters.elevenlabs_tts import ElevenLabsClient, ElevenLabsPronunciation
from thesis_audiobook.ports.tts import TtsRequest


def test_tts_call_raises_under_guard() -> None:
    client = ElevenLabsClient()
    request = TtsRequest(text="hi", voice_id="v", model_id="m")
    with pytest.raises(RuntimeError, match="live external call"):
        client.synthesize(request)


def test_pronunciation_publish_raises_under_guard() -> None:
    with pytest.raises(RuntimeError, match="live external call"):
        ElevenLabsPronunciation().publish("dict", [])


def test_llm_call_raises_under_guard() -> None:
    client = AnthropicClient()
    with pytest.raises(RuntimeError, match="live external call"):
        client.complete("hi")
