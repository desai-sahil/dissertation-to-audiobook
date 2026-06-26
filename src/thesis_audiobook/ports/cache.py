"""Cache port: a content-addressed byte store."""

from __future__ import annotations

from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def put(self, key: str, value: bytes) -> None: ...
