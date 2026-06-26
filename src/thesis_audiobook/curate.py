"""LLM pronunciation curator: a structured, per-document plan for how terms are SAID.

The curator reads the whole document once and returns a PronunciationPlan - a map of
acronym / term / notation spoken forms. It only changes HOW things are pronounced, never
WHAT is said (it does not rewrite prose). The plan is applied deterministically (acronyms
expand on first use, then a short form) and cached content-addressed, so a given document
renders identically and the model runs at most once per document.

Everything here is pure (prompt building, JSON parsing, application). The model call and
the cache live in stages/curate.py behind the LlmClient and Cache ports.
"""

from __future__ import annotations

import re

from thesis_audiobook.ir import StrictModel

CURATOR_VERSION = "curate-v1"


class AcronymRule(StrictModel):
    acronym: str  # token as written in the source, e.g. "ABA"
    first_use: str  # spoken on first occurrence, e.g. "abscisic acid"
    short_form: str  # spoken thereafter, e.g. "A B A"


class TermRule(StrictModel):
    term: str  # e.g. "AtRBOHD"
    spoken: str  # e.g. "arbo D"


class NotationRule(StrictModel):
    written: str  # flattened form as it appears in text, e.g. "psi apo ssc"
    spoken: str  # e.g. "apoplastic subsidiary-cell water potential"


class Dehyphenation(StrictModel):
    broken: str  # word split by a PDF line break, e.g. "me-asurable"
    fixed: str  # the intended word, e.g. "measurable"


class PronunciationPlan(StrictModel):
    acronyms: list[AcronymRule] = []
    terms: list[TermRule] = []
    notation: list[NotationRule] = []
    dehyphenations: list[Dehyphenation] = []
    notes: list[str] = []  # uncertain/flagged items, surfaced in out/<slug>.qa.md

    def is_empty(self) -> bool:
        return not (self.acronyms or self.terms or self.notation or self.dehyphenations)


def build_curate_prompt(document_text: str) -> str:
    return (
        "You are preparing a scientific document to be read aloud as an audiobook. "
        "Return ONLY a JSON object describing how special terms should be SPOKEN. Do NOT "
        "rewrite, summarize, or change any prose - only map tokens to spoken forms.\n\n"
        "JSON shape:\n"
        '{"acronyms":[{"acronym":"ABA","first_use":"abscisic acid","short_form":"A B A"}],'
        '"terms":[{"term":"AtRBOHD","spoken":"arbo D"}],'
        '"notation":[{"written":"psi apo ssc","spoken":"apoplastic subsidiary-cell water '
        'potential"}],"dehyphenations":[{"broken":"me-asurable","fixed":"measurable"}],'
        '"notes":["anything you were unsure about"]}\n\n'
        "Rules:\n"
        "- acronyms: give the full first_use expansion and a short_form spoken as letters "
        '("A B A") unless a lab says it as a word (ROS -> "ross", SPAC -> "spack").\n'
        "- terms: gene/protein names a TTS voice would mispronounce.\n"
        '- notation: flattened math/symbols (e.g. "psi apo ssc") mapped to plain words.\n'
        '- dehyphenations: words a PDF line break split with a stray hyphen ("me-asurable" '
        '-> "measurable", "encom-pass" -> "encompass"). Only real broken words; keep genuine '
        'compounds like "well-known".\n'
        "- Never change meaning. If unsure about a term, add a note and leave it out.\n\n"
        f"Document:\n{document_text}"
    )


def parse_plan(raw: str) -> PronunciationPlan:
    """Parse the model's JSON into a plan; an empty plan on any failure, so a non-JSON
    response (e.g. the offline mock) degrades to no curation rather than crashing."""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return PronunciationPlan()
    try:
        return PronunciationPlan.model_validate_json(text[start : end + 1])
    except Exception:  # noqa: BLE001 - malformed model output -> no curation, not a crash
        return PronunciationPlan()


_BOUNDARY = r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])"


def _key(text: str) -> str:
    return re.sub(r"[\s-]+", " ", text).strip().lower()


def apply_plan(texts: list[str], plan: PronunciationPlan) -> list[str]:
    """Apply the plan to block texts in reading order.

    All mapped tokens (notation, terms, acronyms) are matched by ONE alternation, longest
    first, in a single left-to-right pass per block, so each token is substituted exactly
    once and a substitution's output is never re-scanned (a term's spoken form cannot be
    re-expanded by an acronym rule, nor an acronym's letters by another rule). Acronyms
    expand on first use across the whole document, then read as the short form; empty keys
    are skipped.
    """
    plain: dict[str, str] = {}
    for notation in plan.notation:
        if notation.written.strip():
            plain.setdefault(notation.written, notation.spoken)
    for term in plan.terms:
        if term.term.strip():
            plain.setdefault(term.term, term.spoken)
    for fix in plan.dehyphenations:
        if fix.broken.strip():
            plain.setdefault(fix.broken, fix.fixed)
    acronyms: dict[str, AcronymRule] = {}
    for rule in plan.acronyms:
        if rule.acronym.strip() and rule.acronym not in plain:
            acronyms.setdefault(rule.acronym, rule)

    keys = sorted([*plain, *acronyms], key=len, reverse=True)
    if not keys:
        return list(texts)
    alternation = "(?:" + "|".join(re.escape(key) for key in keys) + ")"
    pattern = re.compile(_BOUNDARY.format(alternation))

    introduced: set[str] = set()
    spoken_prefix = ""
    out: list[str] = []
    for text in texts:

        def repl(match: re.Match[str], text: str = text, prefix: str = spoken_prefix) -> str:
            token = match.group(0)
            rule = acronyms.get(token)
            if rule is None:
                return plain[token]
            if rule.acronym in introduced:
                return rule.short_form
            introduced.add(rule.acronym)
            # Author-aware first use: if the expansion was already spoken anywhere before
            # this point ("abscisic acid (ABA)" in the source, or our own earlier intro),
            # only voice the short form; otherwise introduce it ourselves.
            before = prefix + text[: match.start()]
            if _key(rule.first_use) in _key(before):
                return rule.short_form
            return f"{rule.first_use} ({rule.short_form})"

        new_text = pattern.sub(repl, text)
        out.append(new_text)
        spoken_prefix = f"{spoken_prefix} {new_text}"
    return out
