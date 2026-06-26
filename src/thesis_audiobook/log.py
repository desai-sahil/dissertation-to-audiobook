"""A minimal structured logger. No external deps, no network.

Events are written as `level=... event=... key=value ...` lines to a stream
(stderr by default) so they never pollute CLI stdout.
"""

from __future__ import annotations

import sys
from typing import TextIO


class StructuredLogger:
    def __init__(self, stream: TextIO | None = None, *, enabled: bool = True) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stderr
        self._enabled = enabled

    def _emit(self, level: str, event: str, fields: dict[str, object]) -> None:
        if not self._enabled:
            return
        parts = [f"level={level}", f"event={event}"]
        parts.extend(f"{key}={value}" for key, value in fields.items())
        self._stream.write(" ".join(parts) + "\n")

    def info(self, event: str, **fields: object) -> None:
        self._emit("info", event, fields)

    def warning(self, event: str, **fields: object) -> None:
        self._emit("warning", event, fields)
