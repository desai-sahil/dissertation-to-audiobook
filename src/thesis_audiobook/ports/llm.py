"""LlmClient port: equation gloss and table summary."""

from __future__ import annotations

from typing import Protocol


class LlmClient(Protocol):
    def complete(self, prompt: str) -> str: ...
