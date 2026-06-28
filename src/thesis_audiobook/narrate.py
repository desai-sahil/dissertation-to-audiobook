"""The faithful-rewrite generator (v2 phase C): turn one source segment into spoken text.

This is the inverted transform. The MODEL writes the narration - expand units and numbers, drop
citation markers of any form, announce equations by their printed number, keep every value and
claim, spell numbers out - and the deterministic verifier checks it. A failed segment is regenerated
with the violations fed back; then, for a notation- or citation-dense passage the text model keeps
getting wrong, it escalates to a vision attempt that reads the page image. Still failing, it is
flagged for human review rather than shipped.

Pure: prompt construction, parsing, and the generate/verify/regenerate/escalate loop over INJECTED
model callables (no SDK, no I/O, no Context). The stage binds ctx.llm / ctx.vision and the page
images into those callables. The model only writes; verify_segment is the gate.
"""

from __future__ import annotations

from collections.abc import Callable

from thesis_audiobook.ir import StrictModel
from thesis_audiobook.verifier import Verdict, Violation, verify_segment

NARRATE_VERSION = "narrate-v1"
NARRATE_MAX_TOKENS = 1024  # per-segment spoken text is short; bounds output cost

NARRATE_SYSTEM = (
    "You are narrating a PhD thesis as an audiobook. Rewrite the passage as clear SPOKEN prose a "
    "listener can follow by ear. Rules: keep every number, value, unit, and claim exactly as "
    "written - never change, add, drop, or reorder a value, and never reverse a finding. Spell out "
    "all numbers, symbols, and units in words (say '0.5 mm' as 'zero point five millimeters', '%' "
    "as 'percent', '<' as 'less than'). Drop citation markers and reference numbers of every form "
    "(parenthetical, bracketed, or superscript). Announce a display equation by its printed number "
    "('Equation 3') instead of reading the symbols. Add no commentary or content not in the "
    "passage. Output only the spoken text: no markdown, no preamble, no surrounding quotes."
)


class NarrationResult(StrictModel):
    spoken: str
    ok: bool
    attempts: int
    escalated: bool = False  # a vision attempt was used
    violations: list[Violation] = []  # remaining violations when not ok (-> human review)


def build_narrate_prompt(source: str) -> str:
    return f"Passage to narrate:\n\n{source}"


def build_revision_prompt(source: str, previous: str, verdict: Verdict) -> str:
    problems = "; ".join(f"{v.kind}: {v.detail}" for v in verdict.violations)
    return (
        f"Passage to narrate:\n\n{source}\n\n"
        f"Your previous narration was:\n\n{previous}\n\n"
        f"It broke these faithfulness checks: {problems}. Rewrite it to fix them while keeping "
        "every value and claim and spelling out all numbers, symbols, and units. Output only the "
        "corrected spoken text."
    )


def parse_narration(raw: str) -> str:
    """The model returns spoken text directly; strip code fences / wrapping quotes defensively."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
        text = text[1:-1].strip()
    return text


def narrate_segment(
    source: str,
    *,
    generate: Callable[[str], str],
    vision_generate: Callable[[str], str] | None = None,
    max_text_attempts: int = 2,
) -> NarrationResult:
    """Generate faithful spoken text for `source`, verifier-gated. Text attempts first (with the
    violations fed back on each retry); then one vision attempt if available; else flag for review.

    `generate`/`vision_generate` take a prompt and return the model's raw reply (the stage binds the
    system prompt, token budget, and page images)."""
    attempts = 0
    spoken = ""
    verdict = Verdict(ok=False)
    prompt = build_narrate_prompt(source)
    for _ in range(max(1, max_text_attempts)):
        attempts += 1
        spoken = parse_narration(generate(prompt))
        verdict = verify_segment(source, spoken)
        if verdict.ok:
            return NarrationResult(spoken=spoken, ok=True, attempts=attempts)
        prompt = build_revision_prompt(source, spoken, verdict)

    if vision_generate is not None:
        attempts += 1
        vspoken = parse_narration(vision_generate(build_narrate_prompt(source)))
        vverdict = verify_segment(source, vspoken)
        return NarrationResult(
            spoken=vspoken,
            ok=vverdict.ok,
            attempts=attempts,
            escalated=True,
            violations=[] if vverdict.ok else vverdict.violations,
        )

    return NarrationResult(
        spoken=spoken, ok=False, attempts=attempts, violations=verdict.violations
    )
