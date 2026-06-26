from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from thesis_audiobook.adapters.anthropic_llm import _SYSTEM, AnthropicClient, extract_text


def test_extract_text_concatenates_text_blocks() -> None:
    blocks = [
        SimpleNamespace(type="text", text="The equation "),
        SimpleNamespace(type="text", text="expresses conductance."),
    ]
    assert extract_text(blocks) == "The equation expresses conductance."


def test_extract_text_ignores_non_text_blocks() -> None:
    blocks = [
        SimpleNamespace(type="thinking", thinking="reasoning"),
        SimpleNamespace(type="text", text="Only this sentence."),
    ]
    assert extract_text(blocks) == "Only this sentence."


def test_extract_text_skips_text_block_with_none_text() -> None:
    # A malformed text block with text=None must not leak the literal word "None".
    blocks = [
        SimpleNamespace(type="text", text=None),
        SimpleNamespace(type="text", text="ok"),
    ]
    assert extract_text(blocks) == "ok"


def test_extract_text_empty() -> None:
    assert extract_text([]) == ""


@pytest.mark.contract
def test_complete_maps_sdk_message_offline(cassette_dir: Path) -> None:
    """Contract: complete() sends the right request and maps the SDK Message to text.

    Drives the real AnthropicClient.complete() against a canned, SDK-shaped response
    (the cassette) via an injected fake client, so no network or spend happens. The
    cost guard is skipped for `contract` tests precisely because the client is fake.
    """
    cassette = json.loads((cassette_dir / "anthropic_gloss.json").read_text(encoding="utf-8"))
    captured: dict[str, object] = {}

    class _Messages:
        def create(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            blocks = [SimpleNamespace(**b) for b in cassette["response"]["content"]]
            return SimpleNamespace(content=blocks)

    fake_client = SimpleNamespace(messages=_Messages())
    result = AnthropicClient(client=fake_client).complete(cassette["request"]["prompt"])

    # Response mapping: only the text block survives; the thinking block is dropped.
    assert result == cassette["expected_text"]
    # Request shape: current model, the system prompt, and the user-role prompt.
    assert captured["model"] == "claude-opus-4-8"
    assert captured["system"] == _SYSTEM
    assert captured["messages"] == [{"role": "user", "content": cassette["request"]["prompt"]}]
