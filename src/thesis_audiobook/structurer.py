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
import re
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
_PROMPT_SNIPPET = 400  # fuller text for the few suspects the model actually sees
_LOG_SNIPPET = 140  # shorter, for the change log

# General (not per-thesis) signals that a block typed `paragraph` may actually be code or other
# non-prose the cheap pass missed. Triage flags these for the model; everything else - the
# confident majority - never reaches it. Strong signals flag on their own; weak signals are
# scored and flag only when two or more co-occur, so a stray "->" or "x = f(y)" in real prose
# (a chemistry arrow, an inline definition) is left alone while genuine code - which always
# carries several operators/calls/brackets at once - is caught. False positives only cost one
# classification; false negatives would let code be read aloud, so the bias is toward flagging.
_SPACED_CHARS = re.compile(r"\b\w(?: \w){3,}")  # "i m p o" - parser-shredded characters
# Strong, near-unambiguous code statements (rare in prose); flag on their own. Anchored/qualified
# so "the import of these results" or "we def ine" do not trip them.
_CODE_KEYWORDS = re.compile(
    r"(?m)^\s*(?:import|from)\s+\w|\bimport \w+ as |\bfrom \w+ import\b|\bdef \w+\(|\bprint\(|"
    r"\bfunction \w+\("
)
_CONFIG_LINE = re.compile(r"(?m)^\s*[\w.\-]+\s*[:=]\s*\S")  # "key: value" / "key = value" line
_WEAK_SIGNALS = [
    re.compile(r"[A-Za-z_]\w*\("),  # a function call: name(
    re.compile(r"\b\w+\.\w+\("),  # a method call: obj.method(
    re.compile(r"\w\s*=\s*\w"),  # an assignment: x = y
    re.compile(r"<-|=>|->|<=|>=|&&|\|\||::|!=|\+=|-=|\*="),  # operators
    re.compile(r"[{}]|;.*;"),  # braces, or two+ semicolons (CSS/code, not one prose clause)
    re.compile(r"\$\w+|\$\{"),  # shell variable
    re.compile(r"(?:^|\s)--?[A-Za-z]\w*\b"),  # CLI flag: -c, --verbose
    re.compile(r" \| |\s>>?\s|\s<\s|2>"),  # shell pipe / redirect (also a markdown table row)
    re.compile(r"https?://|www\.|/\w+/\w+"),  # URL or a multi-level file path
    re.compile(r'"\w+"\s*:'),  # JSON key
    re.compile(r"\bSELECT\b.+\bFROM\b", re.IGNORECASE),  # SQL
]


def _is_blob(text: str) -> bool:
    """A single opaque token (base64, a bare file path, a URL-only line) or a comma-stream with
    almost no spaces (a CSV/data row) - never narratable prose."""
    stripped = text.strip()
    if " " not in stripped:
        return len(stripped) >= 24 and any(c.isalpha() for c in stripped)
    return stripped.count(",") >= 4 and stripped.count(" ") <= stripped.count(",") // 2


def _looks_non_prose(text: str) -> bool:
    """A general, conservative test that a paragraph might be code/notation rather than prose.
    Biased toward flagging: a false positive only costs one classification; a false negative
    would let code be read aloud."""
    if "```" in text or _SPACED_CHARS.search(text) or _is_blob(text) or _CODE_KEYWORDS.search(text):
        return True  # strong, unambiguous signals
    score = sum(1 for sig in _WEAK_SIGNALS if sig.search(text))
    if len(_CONFIG_LINE.findall(text)) >= 2:  # a block of key:value / key=value lines
        return True
    if score >= 2:  # several code signals at once -> code, not a stray symbol in prose
        return True
    words = text.split()
    if len(words) >= 4:
        prose_words = sum(1 for w in words if len(w) >= 2 and any(ch.isalpha() for ch in w))
        if prose_words / len(words) < 0.4:  # symbol/number heavy -> a dump, not prose
            return True
    return False


def suspicious_blocks(blocks: list[Block]) -> list[Block]:
    """The subset worth an LLM opinion: paragraph blocks that look like they may be mis-typed.
    The deterministic types stand for everything else, so the model reads a fraction of the doc."""
    return [b for b in blocks if b.type is BlockType.paragraph and _looks_non_prose(b.text)]


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
    """One line per block: id | current type | a text snippet. Deterministic."""
    lines: list[str] = []
    for block in blocks:
        snippet = " ".join(block.current_text().split())[:_PROMPT_SNIPPET]
        lines.append(f"{block.id} | {block.type.value} | {snippet}")
    return "\n".join(lines)


def build_structurer_prompt(outline: str) -> str:
    return (
        "Below are blocks from a thesis that a cheap first pass may have MIS-TYPED - each line is "
        "`id | current-type | text snippet`. They are currently mostly 'paragraph' but some are "
        "really code, a figure/table caption, a bibliography reference, or front matter. For each "
        "id, give its true KIND: prose, heading, equation, code, figure, table, reference, "
        "frontmatter. A spaced-out or fenced program listing is 'code'. Do not quote or rewrite "
        "any text.\n\n"
        'Return ONLY this JSON: {"labels":[{"id":"m1","kind":"code"}, ...]} - one entry per id.\n\n'
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
                snippet=" ".join(block.current_text().split())[:_LOG_SNIPPET],
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
