"""VisionClient port: a Claude call that reads page IMAGES, not just text.

The v1 pipeline only ever sent text (LlmClient.complete). The v2 direction grounds the hard
structural decisions in the rendered page (the source of truth), because almost every failure on a
new thesis is an extraction artifact - a heading the text extractor mis-leveled, a superscript it
flattened, an anchor span it left inline. `describe` sends a batch of page images plus an
instruction and returns the model's text reply (typically JSON the caller parses).

It is a separate port from LlmClient on purpose: the existing text stages and their test fakes need
only `complete`, so widening LlmClient would force a vision method onto every one of them. A real
adapter (AnthropicClient) implements both protocols.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class VisionClient(Protocol):
    def describe(
        self,
        prompt: str,
        images: Sequence[bytes],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> str: ...
