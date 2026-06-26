"""Stage: LLM pronunciation curator.

Builds a PronunciationPlan for the whole document once (through the LlmClient port),
caches it content-addressed via the Cache port, and applies it deterministically to the
kept spoken blocks. The model is mocked in tests (an unparseable mock response yields an
empty plan, so curation is a no-op offline); the cost guard trips on any real call in a
non-live test. Same document + model -> same cached plan -> byte-identical script.
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.curate import (
    CURATOR_VERSION,
    PronunciationPlan,
    apply_plan,
    build_curate_prompt,
    parse_plan,
)
from thesis_audiobook.ir import Document, Handling


class CurateStage:
    name = "curate"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.curate:
            return doc
        blocks = [b for b in doc.blocks if b.keep and b.handling is Handling.speak]
        document_text = "\n\n".join(block.current_text() for block in blocks)
        plan = self._plan(document_text, ctx)
        ctx.pronunciation_plan = plan
        if plan.is_empty() or not blocks:
            return doc
        spoken = apply_plan([block.current_text() for block in blocks], plan)
        for block, text in zip(blocks, spoken, strict=True):
            block.spoken = text
        ctx.log.info(
            "curated",
            acronyms=len(plan.acronyms),
            terms=len(plan.terms),
            notation=len(plan.notation),
            notes=len(plan.notes),
        )
        return doc

    def _plan(self, document_text: str, ctx: Context) -> PronunciationPlan:
        if not document_text.strip():
            return PronunciationPlan()
        # Key by the LLM backend (mock vs real), so an offline mock run's empty plan can
        # never be served to a later real run.
        payload = f"{CURATOR_VERSION}\n{type(ctx.llm).__name__}\n{document_text}"
        key = "curate." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return parse_plan(cached.decode("utf-8"))
        plan = parse_plan(ctx.llm.complete(build_curate_prompt(document_text)))
        # Never cache an empty plan (mock output or a parse failure): leave it to retry.
        if not plan.is_empty():
            ctx.cache.put(key, plan.model_dump_json().encode("utf-8"))
        return plan
