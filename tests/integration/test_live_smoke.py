from __future__ import annotations

import pytest


@pytest.mark.live
def test_live_tts_smoke() -> None:
    """Placeholder. A real one-chunk live render against ElevenLabs lands in M4."""
    pytest.skip("Live TTS smoke test lands in M4.")
