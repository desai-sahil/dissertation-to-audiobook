"""Status reporter port: ephemeral terminal progress for a single run.

A purely presentational side channel. Stages announce the step they are on
(`update`) through this port exactly as they emit structured logs through `log`;
the CLI composition root owns the animation lifecycle (`start` / `stop`). The
default implementation is a no-op (see adapters/status.py), so a Context built
without wiring stays silent and writes zero bytes - it never touches the
Document or the cache, so determinism is unaffected.
"""

from __future__ import annotations

from typing import Protocol


class StatusReporter(Protocol):
    def start(self) -> None: ...
    def update(self, label: str) -> None: ...
    def stop(self) -> None: ...
