"""TtsClient port: text to audio bytes.

The request carries everything that affects the audio bytes: voice, model, settings,
seed, the pronunciation dictionary locators, neighbor text/request-ids for prosody
continuity, and the text-normalization mode. The renderer derives the cache key from
the same fields, so any change re-renders.
"""

from __future__ import annotations

from typing import Protocol

from thesis_audiobook.config import TextNormalization, VoiceSettings
from thesis_audiobook.ir import StrictModel
from thesis_audiobook.pronunciation import DictionaryLocator


class TtsRequest(StrictModel):
    text: str
    voice_id: str
    model_id: str
    voice_settings: VoiceSettings = VoiceSettings()
    output_format: str = "mp3_44100_128"
    apply_text_normalization: TextNormalization = "off"
    seed: int | None = None
    # Prosody continuity: literal neighbor text, or up to 3 prior/next request ids.
    previous_text: str | None = None
    next_text: str | None = None
    previous_request_ids: list[str] = []
    next_request_ids: list[str] = []
    locators: list[DictionaryLocator] = []


class TtsClient(Protocol):
    # A short, stable id for the backend ("mock"/"elevenlabs"). It is part of the renderer's cache
    # key so a mock render's silent audio can never be served to a real ElevenLabs render.
    cache_tag: str

    def synthesize(self, req: TtsRequest) -> bytes: ...
