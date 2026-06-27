"""The Structurer: an LLM block-kind classifier. Pure (prompt, parse, apply); no I/O.

Marker formats each thesis differently - code arrives fenced or as spaced-out prose, equations
inline or display, headings in idiosyncratic schemes - so a regex tuned on one thesis does not
generalize to the next. Instead of writing a new rule per thesis, the Structurer asks the model
to LABEL each block's kind (prose / heading / equation / code / figure / table / reference /
frontmatter); the deterministic layer renders or skips from the label, exactly like the
cartographer renders from region labels.

Claim-safe by construction: the model returns only a kind per existing block id - never prose, a
number, or a name - so it cannot fabricate content. The worst case is a misclassification, and
every change of type is recorded (Reclassification) so the caller can log it for review rather
than have the structure change silently. The cached model call lives in the stage.
"""

from __future__ import annotations

import json
from typing import Any

from thesis_audiobook.ir import Block, BlockType, StrictModel

STRUCTURER_VERSION = "structurer-v1"
STRUCTURER_SYSTEM = (
    "You classify the blocks of a thesis being turned into an audiobook. For each block id you are "
    "given, return its KIND - what it IS, so the pipeline can read prose and skip non-narratable "
    "material. Use: prose, heading, equation, code, figure, table, reference, frontmatter. "
    "'code' is any program/source listing (even if its characters are spaced out by the parser); "
    "'figure' is a figure/table caption; 'reference' is a bibliography entry; 'frontmatter' is a "
    "title page / table of contents / list of figures or tables. Return ONLY a kind per id - never "
    "rewrite or quote the text. Return ONLY the requested JSON; no prose, no markdown fences."
)
STRUCTURER_MAX_TOKENS = 16_384

# The model's kind -> the IR BlockType the deterministic layer renders/skips from.
_KIND_TO_TYPE: dict[str, BlockType] = {
    "prose": BlockType.paragraph,
    "heading": BlockType.heading,
    "equation": BlockType.equation_display,
    "code": BlockType.code,
    "figure": BlockType.figure_caption,
    "table": BlockType.table,
    "reference": BlockType.reference_list,
    "frontmatter": BlockType.frontmatter,
}
_SNIPPET = 140


class BlockLabel(StrictModel):
    id: str
    kind: str


class StructurePlan(StrictModel):
    labels: list[BlockLabel] = []

    def is_empty(self) -> bool:
        return not self.labels


class Reclassification(StrictModel):
    id: str
    from_type: str
    to_type: str
    snippet: str


def build_outline(blocks: list[Block]) -> str:
    """One line per block: id | current type | a short text snippet. Deterministic."""
    lines: list[str] = []
    for block in blocks:
        snippet = " ".join(block.current_text().split())[:_SNIPPET]
        lines.append(f"{block.id} | {block.type.value} | {snippet}")
    return "\n".join(lines)


def build_structurer_prompt(outline: str) -> str:
    return (
        "Below is every block of a thesis, one per line as `id | current-type | text snippet`. "
        "For each id, decide its KIND (prose, heading, equation, code, figure, table, reference, "
        "frontmatter). Most blocks are already right; correct the ones that are mislabelled - in "
        "particular, spaced-out or fenced program listings should be 'code', and bibliography "
        "entries 'reference'. Do not quote or rewrite any text.\n\n"
        'Return ONLY this JSON: {"labels":[{"id":"m1","kind":"prose"}, ...]} - include only the '
        "ids whose kind you are stating (you may include all of them).\n\n"
        "=== BLOCKS ===\n"
        f"{outline}\n"
    )


def parse_structure_plan(raw: str) -> StructurePlan:
    """Parse the model's JSON; an empty plan on any failure (so the offline mock is a no-op)."""
    text = raw
    for fence in ("```json", "```"):
        text = text.replace(fence, "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return StructurePlan()
    try:
        data: Any = json.loads(text[start : end + 1])
        return StructurePlan.model_validate(data)
    except Exception:  # noqa: BLE001 - malformed model output -> no reclassification, not a crash
        return StructurePlan()


def apply_structure(blocks: list[Block], plan: StructurePlan) -> list[Reclassification]:
    """Set each block's type from its label where the model disagrees with the current type, and
    return the change log. Labels for unknown ids or unknown kinds are ignored (claim-safe: only a
    type can change, never the text)."""
    by_id = {block.id: block for block in blocks}
    changes: list[Reclassification] = []
    for label in plan.labels:
        block = by_id.get(label.id)
        new_type = _KIND_TO_TYPE.get(label.kind.strip().lower())
        if block is None or new_type is None or block.type is new_type:
            continue
        changes.append(
            Reclassification(
                id=block.id,
                from_type=block.type.value,
                to_type=new_type.value,
                snippet=" ".join(block.current_text().split())[:_SNIPPET],
            )
        )
        block.type = new_type
    return changes


def render_structure_changes(changes: list[Reclassification]) -> str:
    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = [f"# Structurer reclassifications ({len(changes)})", ""]
    if not changes:
        return (
            "\n".join([*lines, "None - the deterministic block types were left unchanged."]) + "\n"
        )
    lines += ["| block | from | to | snippet |", "|---|---|---|---|"]
    lines += [f"| {c.id} | {c.from_type} | {c.to_type} | {cell(c.snippet)} |" for c in changes]
    return "\n".join(lines) + "\n"
