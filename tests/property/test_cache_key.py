from __future__ import annotations

from thesis_audiobook.config import VoiceSettings
from thesis_audiobook.ports.tts import TtsRequest
from thesis_audiobook.stages.tts import chunk_cache_key

_BASE = TtsRequest(text="hello", voice_id="v", model_id="m")
_TTS = "elevenlabs"


def test_identical_inputs_give_identical_keys() -> None:
    assert chunk_cache_key(_BASE, "d0", _TTS) == chunk_cache_key(_BASE.model_copy(), "d0", _TTS)


def test_key_is_sensitive_to_every_input() -> None:
    # build_spec 7.4 + section 10: text, voice, model, settings, seed, neighbors, normalization
    # mode, output format, dictionary version, and the TTS backend each change the key.
    key = chunk_cache_key(_BASE, "d0", _TTS)
    assert key != chunk_cache_key(_BASE.model_copy(update={"text": "world"}), "d0", _TTS)
    assert key != chunk_cache_key(_BASE.model_copy(update={"voice_id": "other"}), "d0", _TTS)
    assert key != chunk_cache_key(_BASE.model_copy(update={"model_id": "other"}), "d0", _TTS)
    assert key != chunk_cache_key(
        _BASE.model_copy(update={"voice_settings": VoiceSettings(stability=0.9)}), "d0", _TTS
    )
    assert key != chunk_cache_key(_BASE.model_copy(update={"seed": 1}), "d0", _TTS)
    assert key != chunk_cache_key(_BASE.model_copy(update={"previous_text": "prev"}), "d0", _TTS)
    assert key != chunk_cache_key(_BASE.model_copy(update={"next_text": "next"}), "d0", _TTS)
    assert key != chunk_cache_key(
        _BASE.model_copy(update={"output_format": "mp3_22050_32"}), "d0", _TTS
    )
    assert key != chunk_cache_key(
        _BASE.model_copy(update={"apply_text_normalization": "on"}), "d0", _TTS
    )
    assert key != chunk_cache_key(_BASE, "d1", _TTS)  # dictionary version


def test_backend_changes_the_key() -> None:
    # The regression guard: a mock render must NOT share a cache entry with a real ElevenLabs
    # render, or the mock's silent audio would be replayed for the paid render.
    assert chunk_cache_key(_BASE, "d0", "mock") != chunk_cache_key(_BASE, "d0", "elevenlabs")
