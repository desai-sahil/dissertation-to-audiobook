"""Vision-grounded structure pass (v2 cartographer): pure prompt + typed map + defensive parser.

The model reads page images of a thesis and classifies each TOP-LEVEL division with a semantic
KIND (body_chapter, abstract, references, appendix, ...). This is the v2 cartographer's read step,
grounded in the rendered page instead of lossy extracted text - the case v1 got wrong on Zhu, whose
roman-numeral, span-wrapped headings yielded zero detected chapters.

A unified section list (rather than separate "chapters" and "regions") matters because a thesis can
number its back matter in the same sequence as its chapters: Zhu prints "VII. REFERENCES" and
"VIII. APPENDIX". Asking the model what each division *is* lets "VII. REFERENCES" come back as
`references` (skipped), not as a body chapter that would be read aloud. The model only LABELS; a
deterministic policy below decides read/skip, so a relabel can never silently change what is spoken.

Everything here is pure (no I/O, no SDK): image rendering lives in adapters/pdf_render.py, the
billed call behind the VisionClient port, the orchestration in eval/vision_run.py. The parser is
lenient (empty-on-failure) so a stray field or a code fence degrades into a usable or empty map.
"""

from __future__ import annotations

import json
from typing import Any, cast

from thesis_audiobook.ir import StrictModel

VISION_STRUCTURE_VERSION = "vis-struct-v2"

VISION_STRUCTURE_SYSTEM = (
    "You are a meticulous document-structure analyst. You read page images of a PhD thesis and "
    "report its structure as JSON. Output ONLY valid JSON: no markdown, no code fences, no prose."
)

# Every semantic kind the model may assign. body_chapter is the dissertation's argument; the rest
# are front matter or back matter. Any kind the model returns that is not here routes to review.
SECTION_KINDS = (
    "body_chapter",
    "abstract",
    "acknowledgements",
    "dedication",
    "biographical_sketch",
    "table_of_contents",
    "list_of_figures",
    "list_of_tables",
    "references",
    "appendix",
)

# --- read-vs-skip policy (deterministic; the model only LABELS a section's kind) ---
# The author's decision: chapters and front matter are SPOKEN; navigation aids and back matter
# (references, appendix) are skipped. An unknown kind routes to review, never a silent skip.
READ_SECTION_KINDS = frozenset(
    {"body_chapter", "abstract", "acknowledgements", "dedication", "biographical_sketch"}
)
SKIP_SECTION_KINDS = frozenset(
    {"table_of_contents", "list_of_figures", "list_of_tables", "references", "appendix"}
)


class VisionSection(StrictModel):
    number: str  # the printed label as-is: "2", "II", "A" (may be empty for an unnumbered section)
    title: str
    start_page: int | None = None  # absolute page number where the heading is printed
    kind: str = "unknown"  # one of SECTION_KINDS, else 'unknown' -> review


class VisionStructureMap(StrictModel):
    sections: list[VisionSection] = []


def section_decision(kind: str) -> str:
    """'read' | 'skip' | 'review' for a section kind."""
    normalized = kind.strip().lower()
    if normalized in READ_SECTION_KINDS:
        return "read"
    if normalized in SKIP_SECTION_KINDS:
        return "skip"
    return "review"


def body_chapters(structure_map: VisionStructureMap) -> list[VisionSection]:
    """The dissertation's actual chapters - kind == body_chapter only. Excludes a references or
    appendix section even when the thesis numbers it in the same sequence (Zhu's VII/VIII)."""
    return [s for s in structure_map.sections if s.kind.strip().lower() == "body_chapter"]


def read_sections(structure_map: VisionStructureMap) -> list[VisionSection]:
    return [s for s in structure_map.sections if section_decision(s.kind) == "read"]


def skipped_sections(structure_map: VisionStructureMap) -> list[VisionSection]:
    return [s for s in structure_map.sections if section_decision(s.kind) == "skip"]


def review_sections(structure_map: VisionStructureMap) -> list[VisionSection]:
    return [s for s in structure_map.sections if section_decision(s.kind) == "review"]


def chapters_detected(structure_map: VisionStructureMap) -> int:
    return len(body_chapters(structure_map))


def build_structure_prompt(first_page: int, last_page: int) -> str:
    """Instruction for one batch of page images covering absolute pages first..last."""
    kinds = ", ".join(SECTION_KINDS)
    return (
        f"These are pages {first_page} to {last_page} of a PhD thesis, in order. Identify each "
        "TOP-LEVEL division of the thesis that BEGINS on any of these pages, and classify what it "
        "IS. A division begins where its heading is printed near the top of a page, for example "
        "'CHAPTER 2', 'II. BACKGROUND', 'Abstract', or 'REFERENCES'. Do NOT report section or "
        "subsection headings, running headers, table-of-contents entries, or figure/table titles. "
        f"For each division give: number (the printed label or empty string), title, start_page "
        f"(absolute, as shown), and kind, one of: {kinds}. Classify by what the division IS, "
        "not by its number: even if the thesis numbers its references or appendix in the same "
        "sequence as its chapters (for example 'VII. REFERENCES' or 'VIII. APPENDIX'), label "
        "those references and appendix, NOT body_chapter. Return ONLY this JSON shape: "
        '{"sections":[{"number":"II","title":"BACKGROUND","start_page":'
        + str(first_page)
        + ',"kind":"body_chapter"}]}. If no division begins on these pages, return an empty '
        '"sections" list.'
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
    ignored, malformed entries are skipped, non-JSON yields an empty map. An unrecognized kind is
    kept verbatim and resolves to 'review' via section_decision (never a silent skip)."""
    try:
        loaded: object = json.loads(_strip_fences(raw))
    except (json.JSONDecodeError, ValueError):
        return VisionStructureMap()
    if not isinstance(loaded, dict):
        return VisionStructureMap()
    data = cast("dict[str, Any]", loaded)

    raw_sections = data.get("sections")
    items: list[Any] = cast("list[Any]", raw_sections) if isinstance(raw_sections, list) else []
    sections: list[VisionSection] = []
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
        kind = str(entry.get("kind", "")).strip().lower() or "unknown"
        sections.append(VisionSection(number=number, title=title, start_page=start_page, kind=kind))

    return VisionStructureMap(sections=sections)


def merge_maps(maps: list[VisionStructureMap]) -> VisionStructureMap:
    """Combine per-batch maps: dedupe sections by number (then title), order by start page. A
    heading appears on exactly one page, so concatenation across page batches plus dedupe is the
    whole merge."""
    sections: list[VisionSection] = []
    seen: set[str] = set()
    for m in maps:
        for section in m.sections:
            key = section.number.strip().upper() or section.title.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            sections.append(section)
    sections.sort(key=lambda s: (s.start_page is None, s.start_page or 0))
    return VisionStructureMap(sections=sections)
