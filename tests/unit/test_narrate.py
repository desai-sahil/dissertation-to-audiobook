from __future__ import annotations

from thesis_audiobook.narrate import narrate_segment, parse_narration

_SOURCE = "increased by 0.5 units"
_GOOD = "increased by zero point five units"  # passes the verifier
_BAD = "increased by zero point nine units"  # value changed -> verifier fails


def _replayer(replies: list[str]):
    """A generate() callable that returns queued replies in order, then repeats the last."""
    box = {"i": 0}

    def generate(_prompt: str) -> str:
        i = min(box["i"], len(replies) - 1)
        box["i"] += 1
        return replies[i]

    return generate


def test_clean_first_attempt() -> None:
    result = narrate_segment(_SOURCE, generate=_replayer([_GOOD]))
    assert result.ok and result.spoken == _GOOD
    assert result.attempts == 1 and not result.escalated


def test_regenerates_with_violations_fed_back() -> None:
    result = narrate_segment(_SOURCE, generate=_replayer([_BAD, _GOOD]))
    assert result.ok and result.spoken == _GOOD
    assert result.attempts == 2


def test_text_failure_without_vision_is_flagged_for_review() -> None:
    result = narrate_segment(_SOURCE, generate=_replayer([_BAD, _BAD]))
    assert not result.ok
    assert result.attempts == 2 and not result.escalated
    assert any(v.kind == "values" for v in result.violations)


def test_escalates_to_vision_and_succeeds() -> None:
    result = narrate_segment(
        _SOURCE,
        generate=_replayer([_BAD, _BAD]),
        vision_generate=_replayer([_GOOD]),
    )
    assert result.ok and result.spoken == _GOOD
    assert result.escalated and result.attempts == 3


def test_escalation_still_failing_is_flagged() -> None:
    result = narrate_segment(
        _SOURCE,
        generate=_replayer([_BAD, _BAD]),
        vision_generate=_replayer([_BAD]),
    )
    assert not result.ok and result.escalated
    assert any(v.kind == "values" for v in result.violations)


def test_revision_prompt_carries_the_violations() -> None:
    seen: list[str] = []

    def generate(prompt: str) -> str:
        seen.append(prompt)
        return _BAD if len(seen) == 1 else _GOOD

    narrate_segment(_SOURCE, generate=generate)
    assert len(seen) == 2
    assert "previous narration" in seen[1] and "values" in seen[1]  # violations fed back


def test_parse_strips_fences_and_wrapping_quotes() -> None:
    assert parse_narration("```\nhello there\n```") == "hello there"
    assert parse_narration('"hello there"') == "hello there"
    assert parse_narration("  plain spoken text.  ") == "plain spoken text."
