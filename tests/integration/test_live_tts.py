from __future__ import annotations

import os

import pytest


@pytest.mark.live
def test_live_render_one_chunk_with_dictionary() -> None:
    """Publishes the domain dictionary and renders one chunk against the real API.

    Needs an ElevenLabs key (ELEVENLABS_API_KEY or ELEVEN_LABS_API_KEY). Optionally set
    ELEVENLABS_VOICE_ID; defaults to a public voice. Skipped by default; run with
    `pytest -m live`. Renders a single short chunk only, never the whole thesis.
    """
    key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_LABS_API_KEY")
    if not key:
        pytest.skip("ElevenLabs API key not set")

    from thesis_audiobook.adapters.elevenlabs_tts import ElevenLabsClient, ElevenLabsPronunciation
    from thesis_audiobook.bootstrap import load_pronunciation_lexicon
    from thesis_audiobook.ports.tts import TtsRequest
    from thesis_audiobook.pronunciation import DictionaryLocator, PronunciationPublishError

    lexicon = load_pronunciation_lexicon()
    # Publishing needs pronunciation_dictionaries_write; if the key lacks it, still test
    # the render (the core path) without the dictionary.
    locators: list[DictionaryLocator] = []
    try:
        locators = [
            ElevenLabsPronunciation(api_key=key).publish("thesis-audiobook-test", lexicon.rules)
        ]
    except PronunciationPublishError as error:
        print(f"(dictionary publish skipped: {error})")

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    request = TtsRequest(
        text="Stomatal conductance was reduced under drought.",
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        locators=locators,
    )
    audio = ElevenLabsClient(api_key=key).synthesize(request)
    assert isinstance(audio, bytes)
    assert len(audio) > 1000
