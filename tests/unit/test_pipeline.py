from __future__ import annotations

import pytest
from pydantic import ValidationError

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Block, BlockType, Document, DocumentMeta
from thesis_audiobook.pipeline import Pipeline
from thesis_audiobook.stages import build_default_pipeline


def test_pipeline_runs_all_stages(mock_context: Context) -> None:
    pipeline = build_default_pipeline()
    doc = pipeline.run(Document(meta=DocumentMeta(title="(pending)")), mock_context)
    assert doc.script is not None
    assert doc.chunks
    assert all(block.spoken is not None for block in doc.blocks if block.keep)
    assert mock_context.final_audio  # placeholder audio was produced in memory


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_boundary_validation_catches_malformed_output(mock_context: Context) -> None:
    class BadStage:
        name = "bad"

        def run(self, doc: Document, ctx: Context) -> Document:
            bad_block = Block.model_construct(
                id="x", type=BlockType.paragraph, text="t", confidence="high"
            )
            return Document.model_construct(meta=doc.meta, blocks=[bad_block])

    pipeline = Pipeline([BadStage()])
    with pytest.raises(ValidationError):
        pipeline.run(Document(meta=DocumentMeta(title="t")), mock_context)


def test_slice_runs_subrange(mock_context: Context) -> None:
    pipeline = build_default_pipeline()
    doc = pipeline.run(
        Document(meta=DocumentMeta(title="(pending)")),
        mock_context,
        frm="ingest",
        to="select",
    )
    assert doc.script is None  # assemble_script has not run yet
    assert doc.blocks  # ingest populated blocks from the mock parser
