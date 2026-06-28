"""Vision-grounded structure pass (v2 prototype): pure prompt + typed map + defensive parser.

The model reads page images of a thesis and reports its BODY CHAPTERS (under any numbering scheme)
and which non-body region kinds appear, as JSON. This is the v2 cartographer's read step, grounded
in the rendered page instead of lossy extracted text - the case v1 got wrong on Zhu, whose
roman-numeral, span-wrapped headings yielded zero detected chapters.

Everything here is pure (no I/O, no SDK): the image rendering lives in adapters/pdf_render.py, the
billed call behind the VisionClient port, and the orchestration in eval/vision_run.py. The parser is
deliberately lenient (defensive extraction, empty-on-failure) so a stray field or a fenced code
block in the model's reply degrades to a usable or empty map, never a crash.
"""

from __future__ import annotations

import json
from typing import Any, cast

from thesis_audiobook.ir import StrictModel

VISION_STRUCTURE_VERSION = "vis-struct-v1"

VISION_STRUCTURE_SYSTEM = (
    "You are a meticulous document-structure analyst. You read page images of a PhD thesis and "
    "report its structure as JSON. Output ONLY valid JSON: no markdown, no code fences, no prose."
)


class VisionChapter(StrictModel):
    number: str  # the printed chapter label as-is: "2", "II", "Four" (may be empty if untitled)
    title: str
    start_page: int | None = None  # absolute page number where the heading is printed


class VisionStructureMap(StrictModel):
    chapters: list[VisionChapter] = []
    skip_regions: list[str] = []  # non-body kinds seen: references, appendix, table_of_contents...


def build_structure_prompt(first_page: int, last_page: int) -> str:
    """Instruction for one batch of page images covering absolute pages first..last."""
    return (
        f"These are pages {first_page} to {last_page} of a PhD thesis, in order. Identify the BODY "
        "CHAPTERS that BEGIN on any of these pages: the chapter division of the dissertation "
        "itself, under whatever scheme the author used (arabic '1', roman 'I', or a spelled word). "
        "A chapter begins where its heading is printed near the top of a page, for example "
        "'CHAPTER 2' or 'II. BACKGROUND'. Do NOT report table-of-contents entries, running "
        "headers, section or subsection headings, figure or table titles, or reference-list "
        "entries as chapters. Separately, list which non-body REGION KINDS appear on these pages, "
        "choosing from: table_of_contents, list_of_figures, list_of_tables, abstract, "
        "acknowledgements, references, appendix. Use the absolute page numbers shown. Return ONLY "
        "this JSON shape: "
        '{"chapters":[{"number":"II","title":"BACKGROUND","start_page":' + str(first_page) + "}],"
        '"skip_regions":["references"]}. If no chapter begins on these pages, return an empty '
        '"chapters" list.'
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        # drop the opening fence line (``` or ```json) and a trailing fence if present
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_structure_map(raw: str) -> VisionStructureMap:
    """Parse the model's reply into a typed map. Lenient and empty-on-failure: unknown keys are
    ignored, malformed entries are skipped, non-JSON yields an empty map."""
    try:
        loaded: object = json.loads(_strip_fences(raw))
    except (json.JSONDecodeError, ValueError):
        return VisionStructureMap()
    if not isinstance(loaded, dict):
        return VisionStructureMap()
    data = cast("dict[str, Any]", loaded)

    chapters: list[VisionChapter] = []
    raw_chapters = data.get("chapters")
    items: list[Any] = cast("list[Any]", raw_chapters) if isinstance(raw_chapters, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        entry = cast("dict[str, Any]", item)
        number = str(entry.get("number", "")).strip()
        title = str(entry.get("title", "")).strip()
        if not number and not title:
            continue
        sp = entry.get("start_page")
        start_page = sp if isinstance(sp, int) and not isinstance(sp, bool) else None
        chapters.append(VisionChapter(number=number, title=title, start_page=start_page))

    skip_regions: list[str] = []
    raw_skips = data.get("skip_regions")
    skips: list[Any] = cast("list[Any]", raw_skips) if isinstance(raw_skips, list) else []
    for s in skips:
        label = str(s).strip().lower()
        if label and label not in skip_regions:
            skip_regions.append(label)

    return VisionStructureMap(chapters=chapters, skip_regions=skip_regions)


def merge_maps(maps: list[VisionStructureMap]) -> VisionStructureMap:
    """Combine per-batch maps: dedupe chapters by number (then title), order by start page, and
    union the skip regions. A chapter heading appears on exactly one page, so concatenation across
    page batches plus dedupe is the whole merge."""
    chapters: list[VisionChapter] = []
    seen: set[str] = set()
    for m in maps:
        for ch in m.chapters:
            key = ch.number.strip().upper() or ch.title.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            chapters.append(ch)
    chapters.sort(key=lambda c: (c.start_page is None, c.start_page or 0))
    skip_regions = sorted({s for m in maps for s in m.skip_regions})
    return VisionStructureMap(chapters=chapters, skip_regions=skip_regions)


def chapters_detected(structure_map: VisionStructureMap) -> int:
    return len(structure_map.chapters)
