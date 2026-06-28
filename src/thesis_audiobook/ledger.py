"""The update ledger: one reviewable record of every JUDGMENT the pipeline made. Pure, no I/O.

The pipeline leans on the model (Structurer, curator, the writer repair loop) to absorb
per-thesis variability instead of hand-coded rules. The ledger is the accountability for that: a
single `out/<slug>.ledger.md` listing what structure was inferred, which terms were given spoken
forms, and which auto-repairs were applied or rejected - so a human can catch anything wrong
before any audio is paid for. It aggregates what was previously spread across the structure-changes,
qa, and script-repair reports. Plain deterministic text rendering (numbers, symbols) is NOT logged
here; only the decisions that varied per document are.
"""

from __future__ import annotations

from thesis_audiobook.curate import PronunciationPlan
from thesis_audiobook.ir import BlockType, Document
from thesis_audiobook.script_repair import AppliedRepair, RejectedRepair
from thesis_audiobook.structurer import Reclassification


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return out


def _chapters(doc: Document) -> list[tuple[int, str]]:
    """The chapter titles in order: the first un-numbered heading carrying each chapter number."""
    seen: set[int] = set()
    chapters: list[tuple[int, str]] = []
    for block in doc.blocks:
        if (
            block.type is BlockType.heading
            and block.chapter is not None
            and block.section is None
            and block.chapter not in seen
        ):
            seen.add(block.chapter)
            chapters.append((block.chapter, block.text))
    return chapters


def render_ledger(
    doc: Document,
    reclassifications: list[Reclassification],
    plan: PronunciationPlan | None,
    applied: list[AppliedRepair],
    rejected: list[RejectedRepair],
    citation_genericizations: dict[str, str] | None = None,
) -> str:
    lines: list[str] = [
        f"# Update ledger - {doc.meta.title}",
        "",
        "Every judgment the pipeline made beyond plain text rendering: inferred structure, spoken "
        "forms for special terms, and auto-repairs applied or rejected. Review before publishing.",
        "",
    ]

    # --- Structure -------------------------------------------------------------------------------
    chapters = _chapters(doc)
    backmatter = [b for b in doc.blocks if b.type is BlockType.backmatter]
    lines += ["## Structure", ""]
    lines.append(f"- Chapters detected: {len(chapters)}")
    lines += [f"  {n}. {title}" for n, title in chapters]
    if backmatter:
        first = next((b.text for b in backmatter if b.type is BlockType.backmatter), "")
        lines.append(
            f"- Back matter skipped (appendices / bibliography): {len(backmatter)} block(s)"
            + (f', from "{_cell(first)}" onward' if first else "")
        )
    if reclassifications:
        lines += ["", f"- Structurer reclassified {len(reclassifications)} block(s):", ""]
        lines += _table(
            ["block", "from", "to", "snippet"],
            [[c.id, c.from_type, c.to_type, c.snippet] for c in reclassifications],
        )
    lines.append("")

    # --- Pronunciation (curator) -----------------------------------------------------------------
    lines += ["## Pronunciation (curator)", ""]
    if plan is None or plan.is_empty():
        lines += ["None.", ""]
    else:
        if plan.acronyms:
            lines += [f"- Acronyms: {len(plan.acronyms)}", ""]
            lines += _table(
                ["acronym", "first use", "thereafter"],
                [[a.acronym, a.first_use, a.short_form] for a in plan.acronyms],
            )
            lines.append("")
        if plan.terms:
            lines += [f"- Terms: {len(plan.terms)}", ""]
            lines += _table(["term", "spoken"], [[t.term, t.spoken] for t in plan.terms])
            lines.append("")
        if plan.notation:
            lines += [f"- Notation: {len(plan.notation)}", ""]
            lines += _table(["written", "spoken"], [[n.written, n.spoken] for n in plan.notation])
            lines.append("")
        if plan.dehyphenations:
            lines += [f"- Dehyphenations: {len(plan.dehyphenations)}", ""]
            lines += _table(["broken", "fixed"], [[d.broken, d.fixed] for d in plan.dehyphenations])
            lines.append("")
        if plan.notes:
            lines += [f"- Notes (uncertain, please review): {len(plan.notes)}", ""]
            lines += [f"  - {note}" for note in plan.notes]
            lines.append("")

    # --- Citations (genericized) -----------------------------------------------------------------
    generic = citation_genericizations or {}
    lines += ["## Citations (author mentions genericized)", ""]
    if generic:
        lines += _table(["author mention", "read as"], [[k, v] for k, v in generic.items()])
    else:
        lines.append("None genericized (reference markers are still stripped deterministically).")
    lines.append("")

    # --- Auto-repairs, grouped by what was changed (provenance for review) -----------------------
    def _applied_table(title: str, kinds: set[str]) -> None:
        rows = [a for a in applied if a.kind in kinds]
        lines.extend([f"## {title}", ""])
        if rows:
            lines.append(f"- Applied: {len(rows)}")
            lines.append("")
            lines.extend(
                _table(
                    ["find", "replace", "count", "reason"],
                    [[a.find, a.replace, str(a.count), a.reason] for a in rows],
                )
            )
        else:
            lines.append("None.")
        lines.append("")

    _applied_table("Auto-repairs (notation vocalization)", {"notation"})
    # The audiobook reads the thesis AS WRITTEN except for these MECHANICAL fixes; the deterministic
    # copy-edit guard kept every number, sign, and claim unchanged. Review before publishing.
    _applied_table("Author corrections (copy-edit: spelling / grammar / spacing)",
                   {"spelling", "grammar", "spacing"})  # fmt: skip
    _applied_table("Extraction artifacts re-rendered", {"extraction_artifact"})

    lines += ["## Rejected / flagged (sent to human review, not applied)", ""]
    if rejected:
        lines += _table(["find", "replace", "why"], [[r.find, r.replace, r.why] for r in rejected])
    else:
        lines.append("None.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
