"""PronunciationPublisher port: push alias/phoneme rules to a pronunciation dictionary.

The lexicon stage builds rules from the versioned data file and publishes them through
this port, receiving a DictionaryLocator (dictionary id + version id) that the renderer
attaches to every TTS request. Real publishing hits ElevenLabs; the mock returns a
deterministic locator offline.
"""

from __future__ import annotations

from typing import Protocol

from thesis_audiobook.pronunciation import DictionaryLocator, PronunciationRule


class PronunciationPublisher(Protocol):
    def publish(self, name: str, rules: list[PronunciationRule]) -> DictionaryLocator: ...
