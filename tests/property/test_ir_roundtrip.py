from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta


@given(texts=st.lists(st.text(), max_size=8))
def test_document_round_trips(texts: list[str]) -> None:
    blocks = [
        Block(id=f"b{index}", type=BlockType.paragraph, text=text)
        for index, text in enumerate(texts)
    ]
    doc = Document(meta=DocumentMeta(title="Property Thesis"), blocks=blocks)
    assert Document.model_validate(doc.model_dump()) == doc
