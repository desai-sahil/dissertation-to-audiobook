"""Pure pronunciation-lexicon model and helpers. No I/O, no network.

The domain pronunciation dictionary is a versioned data file under source control
(data/pronunciation.json), loaded at the composition root and validated into this
model. Alias rules ("gs" -> "stomatal conductance") work on eleven_multilingual_v2;
phoneme rules are reserved for the few Greek symbols. The PronunciationPublisher port
pushes these rules to ElevenLabs and returns a DictionaryLocator; the renderer passes
the locator on every request. The file's `version` (not the API-assigned version id)
feeds the deterministic TTS cache key, so a rules edit forces a clean re-render.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from thesis_audiobook.ir import StrictModel


class PronunciationPublishError(RuntimeError):
    """Publishing the dictionary to the provider failed. The render can proceed without
    it, since the script is already normalized; the renderer just omits the locator."""


class AliasRule(StrictModel):
    type: Literal["alias"] = "alias"
    string_to_replace: str
    alias: str


class PhonemeRule(StrictModel):
    type: Literal["phoneme"] = "phoneme"
    string_to_replace: str
    phoneme: str
    alphabet: str = "ipa"


PronunciationRule = Annotated[AliasRule | PhonemeRule, Field(discriminator="type")]


class DictionaryLocator(StrictModel):
    """Identifies a published ElevenLabs pronunciation dictionary version."""

    pronunciation_dictionary_id: str
    version_id: str


class PronunciationLexicon(StrictModel):
    version: str
    rules: list[PronunciationRule]


def rules_to_api_payload(rules: list[PronunciationRule]) -> list[dict[str, str]]:
    """Pure: the list-of-dicts shape the ElevenLabs add-from-rules endpoint expects."""
    return [rule.model_dump() for rule in rules]
