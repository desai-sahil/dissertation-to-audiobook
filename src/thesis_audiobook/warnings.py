"""Low-confidence findings are data, not exceptions.

The WarningsSink collects typed findings during a run; the CLI prints them at the
review gate. Parsing never silently reorders or drops content above threshold
without recording a finding here.
"""

from __future__ import annotations

from thesis_audiobook.ir import StrictModel


class LowConfidence(StrictModel):
    block_id: str
    reason: str
    score: float


class WarningsSink:
    def __init__(self) -> None:
        self._items: list[LowConfidence] = []

    def add(self, warning: LowConfidence) -> None:
        self._items.append(warning)

    @property
    def items(self) -> list[LowConfidence]:
        return list(self._items)

    def report(self) -> str:
        if not self._items:
            return "No low-confidence findings."
        return "\n".join(f"  {w.block_id}: {w.reason} (score {w.score:.2f})" for w in self._items)
