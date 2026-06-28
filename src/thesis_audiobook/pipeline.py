"""The Stage protocol and the Pipeline runner.

Each stage is a small object with a `name` and a `run(doc, ctx) -> doc`, so stages
are independently testable and composable. The runner re-validates the Document
against the Pydantic schema at every boundary, so a malformed transform fails fast
in its own stage rather than three stages later.
"""

from __future__ import annotations

from typing import Protocol

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document


class Stage(Protocol):
    name: str

    def run(self, doc: Document, ctx: Context) -> Document: ...


class Pipeline:
    def __init__(self, stages: list[Stage]) -> None:
        self.stages = stages

    def _slice(self, frm: str | None, to: str | None) -> list[Stage]:
        names = [stage.name for stage in self.stages]
        start = names.index(frm) if frm is not None else 0
        end = names.index(to) + 1 if to is not None else len(self.stages)
        return self.stages[start:end]

    def run(
        self,
        doc: Document,
        ctx: Context,
        *,
        frm: str | None = None,
        to: str | None = None,
    ) -> Document:
        for stage in self._slice(frm, to):
            ctx.status.update(stage.name)  # coarse per-stage label; loops refine it inside run()
            doc = stage.run(doc, ctx)
            # Boundary validation: a malformed transform raises here, not downstream.
            doc = Document.model_validate(doc.model_dump())
            ctx.log.info("stage_done", stage=stage.name, blocks=len(doc.blocks))
        return doc
