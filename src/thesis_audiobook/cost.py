"""Pure cost estimation for the dry-run path. No I/O, fully deterministic."""

from __future__ import annotations

from thesis_audiobook.ir import StrictModel


class CostEstimate(StrictModel):
    characters: int
    usd_per_character: float
    estimated_usd: float
    note: str


def estimate_cost(script_text: str, usd_per_character: float) -> CostEstimate:
    characters = len(script_text)
    return CostEstimate(
        characters=characters,
        usd_per_character=usd_per_character,
        estimated_usd=round(characters * usd_per_character, 4),
        note="Placeholder rate, not live ElevenLabs pricing.",
    )
