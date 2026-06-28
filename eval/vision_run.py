"""Vision structure prototype (v2, phase 3): does reading page images recover a thesis's chapters
where the v1 text pipeline failed? Renders a PDF to page images, asks Claude (in page batches, since
a request caps at 100 images) for the body chapters and skip regions, merges the batches, and scores
the chapter count against the committed corpus labels.

`collect_structure` is pure given an injected VisionClient + the page images, so the whole
parse/merge/score path is unit-tested offline with a fake client. `main` is the billed path the user
runs: it renders with poppler and calls the real AnthropicClient.

    uv run python -m eval.vision_run            # default: Zhu (the thesis that scores 0/6 in v1)
    uv run python -m eval.vision_run zhu sample/Zhu_cornell_0058O_10014.pdf 100
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.score import Labels, StructureResult, score_structure
from thesis_audiobook.ports.vision import VisionClient
from thesis_audiobook.vision_structure import (
    VISION_STRUCTURE_SYSTEM,
    VisionStructureMap,
    build_structure_prompt,
    chapters_detected,
    merge_maps,
    parse_structure_map,
)

HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
IMAGE_BATCH = 50  # images per request; well under Claude's 100-image cap, keeps tokens modest
STRUCTURE_MAX_TOKENS = 2048


def collect_structure(
    images: list[bytes],
    vision: VisionClient,
    *,
    batch: int = IMAGE_BATCH,
    max_tokens: int = STRUCTURE_MAX_TOKENS,
) -> VisionStructureMap:
    """Read structure from page images in batches and merge. Pure given the injected client."""
    maps: list[VisionStructureMap] = []
    for start in range(0, len(images), batch):
        chunk = images[start : start + batch]
        first, last = start + 1, start + len(chunk)
        prompt = build_structure_prompt(first, last)
        raw = vision.describe(prompt, chunk, system=VISION_STRUCTURE_SYSTEM, max_tokens=max_tokens)
        maps.append(parse_structure_map(raw))
    return merge_maps(maps)


def main() -> None:  # pragma: no cover - billed path (renders + real vision call); user-run
    thesis_id = sys.argv[1] if len(sys.argv) > 1 else "zhu"
    pdf_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("sample/Zhu_cornell_0058O_10014.pdf")
    )
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    from thesis_audiobook.adapters.anthropic_llm import AnthropicClient
    from thesis_audiobook.adapters.pdf_render import render_pdf_pages

    print(f"rendering {pdf_path} at {dpi} dpi ...")
    images = render_pdf_pages(pdf_path, dpi=dpi)
    print(f"  {len(images)} pages; reading structure in batches of {IMAGE_BATCH} ...")

    vision = AnthropicClient(max_tokens=STRUCTURE_MAX_TOKENS)
    structure = collect_structure(images, vision)

    labels = Labels.model_validate_json((CORPUS / thesis_id / "labels.json").read_text("utf-8"))
    result = StructureResult(chapters_detected=chapters_detected(structure))
    score = score_structure(result, labels)

    print(f"\n=== vision structure: {thesis_id} ===")
    for ch in structure.chapters:
        print(f"  {ch.number:>4}  {ch.title}  (p{ch.start_page})")
    print(f"skip regions: {', '.join(structure.skip_regions) or '(none)'}")
    print(
        f"\nstructure score: {score.passed}/{score.total} = {score.rate} "
        f"(v1 baseline was 0/{len(labels.expected_chapters)} = 0.0)"
    )

    out = CORPUS / thesis_id / "vision_structure.json"
    out.write_text(json.dumps(structure.model_dump(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
