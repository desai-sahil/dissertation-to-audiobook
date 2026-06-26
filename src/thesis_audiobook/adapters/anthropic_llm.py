"""Anthropic LlmClient adapter: equation glosses and table summaries via Claude.

Talks to Claude through the official anthropic SDK using the current model
(claude-opus-4-8). The SDK handles retries and backoff (429, 5xx, connection
errors), so the domain stays pure and retry-free. The SDK is imported lazily, so
the package stays importable without it and so the autouse cost guard can patch
`complete` to fail any non-live test that reaches the real LLM. The response
text-extraction step is a pure function, contract-tested offline.
"""
# The anthropic SDK response objects are dynamically typed at our call sites.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

_MODEL = "claude-opus-4-8"
_SYSTEM = (
    "You convert scientific content into a single, clear spoken sentence for an "
    "audiobook. Say what it means, not how it is typeset. Do not read symbols or "
    "LaTeX aloud. No preamble, no markdown. Output only the sentence."
)


class AnthropicUnavailableError(RuntimeError):
    """The anthropic SDK is not installed."""


def extract_text(blocks: Iterable[Any]) -> str:
    """Pure: concatenate the text of a Claude response's text blocks.

    Non-text blocks (thinking, tool_use) and text blocks whose text is missing/None
    are skipped, so nothing like the literal word "None" can leak into the audio.
    """
    parts: list[str] = []
    for block in blocks:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
    return "".join(parts).strip()


class AnthropicClient:
    def __init__(
        self,
        *,
        model: str = _MODEL,
        max_tokens: int = 256,
        max_retries: int = 4,
        system: str = _SYSTEM,
        client: Any | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._max_retries = max_retries
        self._system = system
        # An injected SDK-shaped client lets the offline contract test exercise the
        # request/response mapping without networking; production leaves it None.
        self._injected = client

    def complete(self, prompt: str) -> str:
        message = self._client().messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self._system,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text(message.content)

    def _client(self) -> Any:
        if self._injected is not None:
            return self._injected
        return self._build_live_client()  # pragma: no cover - live only

    def _build_live_client(self) -> Any:  # pragma: no cover - live only
        try:
            import anthropic
        except ImportError as error:
            raise AnthropicUnavailableError(
                "the anthropic SDK is not installed (pip install anthropic)"
            ) from error
        # The SDK auto-retries 429/5xx/connection errors with exponential backoff.
        return anthropic.Anthropic(max_retries=self._max_retries)
