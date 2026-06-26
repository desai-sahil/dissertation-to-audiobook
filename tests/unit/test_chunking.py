from __future__ import annotations

from thesis_audiobook.chunking import ScriptSegment, plan_chunks, plan_chunks_from_text


def test_conservation_and_limit() -> None:
    segments = [
        ScriptSegment("Hello world. ", "a", 1),
        ScriptSegment("Second sentence here.", "b", 1),
    ]
    chunks = plan_chunks(segments, 20)
    assert "".join(c.text for c in chunks) == "Hello world. Second sentence here."
    assert all(len(c.text) <= 20 for c in chunks)


def test_neighbor_pointers() -> None:
    chunks = plan_chunks_from_text("One. Two. Three. Four.", 6)
    assert chunks[0].prev_id is None
    assert chunks[-1].next_id is None
    for index in range(1, len(chunks)):
        assert chunks[index].prev_id == chunks[index - 1].id
        assert chunks[index - 1].next_id == chunks[index].id


def test_hard_split_of_oversized_segment() -> None:
    chunks = plan_chunks([ScriptSegment("x" * 50)], 10)
    assert "".join(c.text for c in chunks) == "x" * 50
    assert all(len(c.text) <= 10 for c in chunks)


def test_block_ids_tracked() -> None:
    chunks = plan_chunks([ScriptSegment("hi ", "a"), ScriptSegment("there", "b")], 100)
    assert chunks[0].block_ids == ["a", "b"]


def test_empty_input() -> None:
    assert plan_chunks([], 10) == []
