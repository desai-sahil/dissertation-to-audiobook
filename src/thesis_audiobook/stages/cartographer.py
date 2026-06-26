"""Stage: LLM thesis cartographer (structure map).

Builds a structural map of the whole document once (through the LlmClient port), caches it
content-addressed via the Cache port, and applies it deterministically to block types so the
downstream select stage decides keep/handling unchanged. Runs after build_ir (so blocks are
clean) and before select (so corrected structure flows into inclusion). The model is mocked
in tests (an unparseable mock response yields an empty map, so the stage is a strict no-op
offline); the cost guard trips on any real call in a non-live test. Same document + model ->
same cached map -> byte-identical output. The stage does NO I/O; the CLI writes structure.md.
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.cartographer import (
    CARTOGRAPHER_MAX_TOKENS,
    CARTOGRAPHER_SYSTEM,
    CARTOGRAPHER_VERSION,
    OUTLINE_CHAR_CEILING,
    apply_map,
    build_cartographer_prompt,
    build_fingerprint,
    build_outline,
    parse_map,
)
from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document, StructureMap
from thesis_audiobook.warnings import LowConfidence


class CartographerStage:
    name = "cartographer"

    def run(self, doc: Document, ctx: Context) -> Document:
        if not ctx.config.structure_eval or not doc.blocks:
            return doc
        outline = build_outline(doc)
        if len(outline) > OUTLINE_CHAR_CEILING:
            ctx.warnings.add(
                LowConfidence(
                    block_id=doc.blocks[0].id,
                    reason=(
                        f"cartographer: outline is {len(outline)} chars "
                        f"(> {OUTLINE_CHAR_CEILING}); structure map may be incomplete"
                    ),
                    score=0.3,
                )
            )
        structure_map = self._map(doc, outline, ctx)
        ctx.structure_map = structure_map
        if structure_map.is_empty():
            return doc
        for warning in apply_map(doc, structure_map):
            ctx.warnings.add(warning)
        ctx.log.info("cartographed", regions=len(structure_map.regions))
        return doc

    def _map(self, doc: Document, outline: str, ctx: Context) -> StructureMap:
        # Cache key over the FULL structural content (not the lossy outline) so distinct
        # documents can never collide; fold in the backend so a mock map is never served
        # to a real run.
        payload = f"{CARTOGRAPHER_VERSION}\n{type(ctx.llm).__name__}\n{build_fingerprint(doc)}"
        key = "cartographer." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return self._verify(parse_map(cached.decode("utf-8")), doc)
        structure_map = parse_map(
            ctx.llm.complete(
                build_cartographer_prompt(outline, doc.meta.title, doc.meta.author),
                system=CARTOGRAPHER_SYSTEM,
                max_tokens=CARTOGRAPHER_MAX_TOKENS,
            )
        )
        # Never cache an empty map (mock output or parse failure): leave it to retry.
        if not structure_map.is_empty():
            ctx.cache.put(key, structure_map.model_dump_json().encode("utf-8"))
        return structure_map

    @staticmethod
    def _verify(structure_map: StructureMap, doc: Document) -> StructureMap:
        # Defence in depth against a cache collision: only trust a cached map whose region
        # ids actually exist in THIS document; otherwise treat it as a miss (empty -> no-op).
        ids = {b.id for b in doc.blocks}
        for region in structure_map.regions:
            if region.first_block_id not in ids or region.last_block_id not in ids:
                return StructureMap()
        return structure_map
