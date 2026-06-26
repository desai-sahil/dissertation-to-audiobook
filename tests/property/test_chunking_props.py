from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from thesis_audiobook.chunking import plan_chunks_from_text


@given(text=st.text(max_size=400), limit=st.integers(min_value=1, max_value=40))
def test_chunk_planner_conserves(text: str, limit: int) -> None:
    chunks = plan_chunks_from_text(text, limit)
    # Conservation: concatenated chunks reproduce the input exactly.
    assert "".join(chunk.text for chunk in chunks) == text
    # Every chunk is at or under the limit.
    assert all(len(chunk.text) <= limit for chunk in chunks)
    # Neighbor pointers are consistent.
    for index, chunk in enumerate(chunks):
        assert chunk.prev_id == (chunks[index - 1].id if index > 0 else None)
        assert chunk.next_id == (chunks[index + 1].id if index + 1 < len(chunks) else None)
