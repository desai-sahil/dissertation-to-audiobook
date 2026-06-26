"""LlmClient port: equation gloss, table summary, and structured (JSON) stages.

`complete` takes an optional per-call `system` and `max_tokens` so one client can serve
both the short gloss stages (their adapter defaults: a "one spoken sentence" system and a
small token cap) and the structured stages (cartographer/curate), which need a JSON system
and a much larger budget. Without per-call overrides a 256-token gloss cap silently
truncates a structure map into invalid JSON.
"""

from __future__ import annotations

from typing import Protocol


class LlmClient(Protocol):
    def complete(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> str: ...
