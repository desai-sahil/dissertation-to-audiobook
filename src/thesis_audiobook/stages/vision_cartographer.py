"""Stage: vision cartographer (v2 engine).

Reads the rendered page images (ctx.page_images, produced by the CLI edge) through the VisionClient
port, builds the semantic structure map, caches it content-addressed, and stores it on ctx for the
narrate stage. No-op unless engine == 'v2'. Does NO I/O itself (page rendering is the composition
root's job); offline the port is MockVision, so with no images the map is empty and the stage is a
strict no-op without billing. Same PDF + model -> same cached map -> a re-run re-bills nothing.
"""

from __future__ import annotations

import hashlib

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document
from thesis_audiobook.vision_structure import (
    VISION_STRUCTURE_VERSION,
    VisionStructureMap,
    collect_structure,
)


class VisionCartographerStage:
    name = "vision_cartographer"

    def run(self, doc: Document, ctx: Context) -> Document:
        if ctx.config.engine != "v2" or not doc.blocks:
            return doc
        structure = self._structure(ctx)
        ctx.vision_structure = structure
        ctx.log.info("vision_cartographed", sections=len(structure.sections))
        return doc

    def _structure(self, ctx: Context) -> VisionStructureMap:
        payload = (
            f"{VISION_STRUCTURE_VERSION}\n{type(ctx.vision).__name__}\n"
            f"{hashlib.sha256(ctx.pdf_bytes).hexdigest()}\n{ctx.config.vision_dpi}"
        )
        key = "vision_structure." + hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cached = ctx.cache.get(key)
        if cached is not None:
            return VisionStructureMap.model_validate_json(cached.decode("utf-8"))
        structure = collect_structure(ctx.page_images, ctx.vision)
        if structure.sections:  # never cache an empty map (mock / no images): leave it to retry
            ctx.cache.put(key, structure.model_dump_json().encode("utf-8"))
        return structure
