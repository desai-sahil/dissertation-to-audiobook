"""Real ElevenLabs adapters: TTS rendering and pronunciation-dictionary publishing.

Both talk to ElevenLabs through the official `elevenlabs` SDK, imported lazily so the
package stays importable without it and so the autouse cost guard can patch the entry
methods (`ElevenLabsClient.synthesize`, `ElevenLabsPronunciation.publish`) to fail any
non-live test that reaches the real API. Retries and backoff live here, in the edge,
not in the domain. Exercised only on the live path; the offline pipeline uses the mocks.
"""
# The elevenlabs SDK objects are dynamically typed at our call sites.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingImports=false

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from thesis_audiobook.ports.tts import TtsRequest
from thesis_audiobook.pronunciation import (
    DictionaryLocator,
    PronunciationPublishError,
    PronunciationRule,
    rules_to_api_payload,
)


class ElevenLabsUnavailableError(RuntimeError):
    """The elevenlabs SDK is not installed."""


def _make_client(api_key: str | None) -> Any:  # pragma: no cover - live only
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as error:
        raise ElevenLabsUnavailableError(
            "the elevenlabs SDK is not installed (pip install elevenlabs)"
        ) from error
    return ElevenLabs(api_key=api_key)


def _is_retryable(error: Exception) -> bool:  # pragma: no cover - live only
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status == 429 or 500 <= status < 600
    # No status code: retry only genuinely transient network/timeout errors, not
    # permanent programming errors (ValueError, AttributeError, ...).
    name = error.__class__.__name__.lower()
    return any(k in name for k in ("timeout", "connection", "connect", "network", "protocol"))


def _with_retries[T](  # pragma: no cover - live only
    call: Callable[[], T], *, attempts: int, base_delay: float
) -> T:
    last: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            return call()
        except Exception as error:  # noqa: BLE001 - re-raised below if not retryable
            last = error
            if attempt >= attempts or not _is_retryable(error):
                raise
            time.sleep(base_delay * (2**attempt))
    raise last if last is not None else RuntimeError("unreachable")


class ElevenLabsClient:
    cache_tag = "elevenlabs"

    def __init__(
        self, *, api_key: str | None = None, max_retries: int = 4, base_delay: float = 0.5
    ) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._base_delay = base_delay

    def synthesize(self, req: TtsRequest) -> bytes:  # pragma: no cover - live only
        client = _make_client(self._api_key)
        locators = [loc.model_dump() for loc in req.locators] or None

        def call() -> bytes:
            stream = client.text_to_speech.convert(
                voice_id=req.voice_id,
                model_id=req.model_id,
                text=req.text,
                output_format=req.output_format,
                voice_settings=req.voice_settings.model_dump(),
                seed=req.seed,
                previous_text=req.previous_text,
                next_text=req.next_text,
                previous_request_ids=req.previous_request_ids or None,
                next_request_ids=req.next_request_ids or None,
                apply_text_normalization=req.apply_text_normalization,
                pronunciation_dictionary_locators=locators,
            )
            return b"".join(stream)

        return _with_retries(call, attempts=self._max_retries, base_delay=self._base_delay)


class ElevenLabsPronunciation:
    def __init__(
        self, *, api_key: str | None = None, max_retries: int = 4, base_delay: float = 0.5
    ) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._base_delay = base_delay

    def publish(  # pragma: no cover - live only
        self, name: str, rules: list[PronunciationRule]
    ) -> DictionaryLocator:
        client = _make_client(self._api_key)

        def call() -> DictionaryLocator:
            created = client.pronunciation_dictionaries.create_from_rules(
                name=name, rules=rules_to_api_payload(rules)
            )
            return DictionaryLocator(
                pronunciation_dictionary_id=created.id, version_id=created.version_id
            )

        try:
            return _with_retries(call, attempts=self._max_retries, base_delay=self._base_delay)
        except Exception as error:
            # A failed publish (e.g. a key lacking pronunciation_dictionaries_write) must
            # not abort the render; the lexicon stage downgrades this to a warning.
            raise PronunciationPublishError(str(error)) from error
