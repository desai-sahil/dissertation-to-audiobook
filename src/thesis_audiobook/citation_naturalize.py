"""LLM citation naturalizer (pure prompt/parse/render).

Numeric citation markers like [12] read robotically aloud. The model's ONLY job here is to
choose a position-appropriate STYLE for each marker (narrative at a sentence start, "as
shown by ..." mid-clause, etc.). It writes no text: the phrase is rendered deterministically
from the resolved author phrase and spelled year, so a marker's replacement can carry NOTHING
beyond the citation itself - it is structurally impossible for the model to inject a clause or
alter the sentence's claim. An unknown style, or a missing author/year, renders nothing and
the caller falls back to the plain deterministic rendering. The model call and the cache live
in stages/citations.py.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast

NATURALIZE_VERSION = "cite-v2"

# Each style is a fixed template filled only with the author phrase and spelled year - no
# free text from the model ever reaches the script.
CITATION_STYLES: dict[str, str] = {
    "narrative": "{authors}, in {year},",
    "as_shown_by": "as shown by {authors} in {year}",
    "as_reported_by": "as reported by {authors} in {year}",
    "trailing": "{authors} {year}",
}


def build_naturalize_prompt(blocks: list[dict[str, object]]) -> str:
    keys = ", ".join(f'"{key}"' for key in CITATION_STYLES)
    payload = json.dumps(blocks, ensure_ascii=False)
    return (
        "You are preparing a scientific document to be read aloud. Each paragraph below has "
        "numeric citation markers like [12]. For EVERY marker, choose the citation STYLE that "
        "reads best where the marker sits in the sentence. You are NOT writing any text - you "
        "only name a style, and the author and year are filled in for you:\n"
        '- "narrative": names then year, for a marker at the START of a sentence '
        '("Jain and Smith, in twenty twenty-one, showed ...")\n'
        '- "as_shown_by" / "as_reported_by": for a marker in the MIDDLE or at the END of a '
        "clause\n"
        '- "trailing": plain "<authors> <year>", when nothing else fits\n'
        f"Return ONLY JSON mapping block id -> marker -> one style key from [{keys}], "
        'e.g. {"b1": {"12": "as_shown_by"}}.\n\n'
        f"Paragraphs:\n{payload}"
    )


def parse_naturalization(raw: str) -> dict[str, dict[str, str]]:
    """Parse the model's {block_id: {marker: style_key}} JSON; empty on any failure."""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        loaded = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for block_id, markers in cast("dict[str, Any]", loaded).items():
        if isinstance(markers, dict):
            marker_map = cast("dict[str, Any]", markers)
            out[str(block_id)] = {
                str(marker): style for marker, style in marker_map.items() if isinstance(style, str)
            }
    return out


def render_citation(style: str, authors: str, year: str) -> str | None:
    """Render the bounded phrase for a model-chosen style. Returns None for an unknown style
    or a missing required field, so the caller uses the deterministic fallback."""
    template = CITATION_STYLES.get(style)
    if template is None:
        return None
    if "{authors}" in template and not authors:
        return None
    if "{year}" in template and not year:
        return None
    return re.sub(r"\s+", " ", template.format(authors=authors, year=year)).strip()
