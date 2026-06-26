"""Convert Marker's LaTeX + HTML markup into plain, spoken-friendly text. Pure, no I/O.

Marker renders math as LaTeX ($$...$$ display, $...$ inline) and uses <sup>/<sub>/<br>
markup; poppler produces none of this, so clean_markup is a no-op on clean prose and is
safe to run parser-agnostically. Display equations are detected separately
(split_display_math) and routed to the math gloss stage; this module turns INLINE math and
markup into plain tokens (e.g. "psi xyl", "g s", "m squared") so raw LaTeX never reaches the
audio. The curator/lexicon then map those tokens to their final spoken forms.
"""

from __future__ import annotations

import re

# Greek command -> spoken name (the normalizer's greek module handles the unicode letters;
# Marker emits the LaTeX command form, so we map it here).
_GREEK = {
    "alpha": "alpha",
    "beta": "beta",
    "gamma": "gamma",
    "Gamma": "gamma",
    "delta": "delta",
    "Delta": "delta",
    "epsilon": "epsilon",
    "varepsilon": "epsilon",
    "zeta": "zeta",
    "eta": "eta",
    "theta": "theta",
    "Theta": "theta",
    "iota": "iota",
    "kappa": "kappa",
    "lambda": "lambda",
    "Lambda": "lambda",
    "mu": "mu",
    "nu": "nu",
    "xi": "xi",
    "pi": "pi",
    "Pi": "pi",
    "rho": "rho",
    "sigma": "sigma",
    "Sigma": "sigma",
    "tau": "tau",
    "phi": "phi",
    "Phi": "phi",
    "varphi": "phi",
    "chi": "chi",
    "psi": "psi",
    "Psi": "psi",
    "omega": "omega",
    "Omega": "omega",
}
# Multi-character operators/relations -> spoken words (order: longest first to avoid \le
# matching inside \leq).
_OPERATORS = [
    (r"\\approx", " approximately "),
    (r"\\equiv", " defined as "),
    (r"\\leq", " less than or equal to "),
    (r"\\geq", " greater than or equal to "),
    (r"\\neq", " not equal to "),
    (r"\\le", " less than or equal to "),
    (r"\\ge", " greater than or equal to "),
    (r"\\times", " times "),
    (r"\\cdot", " times "),
    (r"\\pm", " plus or minus "),
    (r"\\propto", " proportional to "),
    (r"\\rightarrow", " approaches "),
    (r"\\to", " approaches "),
    (r"\\sim", " of order "),
    (r"\\ln", " natural log "),
    (r"\\log", " log "),
    (r"\\sqrt", " square root "),
    (r"\\partial", " partial "),
    (r"\\nabla", " del "),
    (r"\\sum", " sum "),
    (r"\\int", " integral "),
]
_DISPLAY_MATH = re.compile(r"^\$\$(?P<body>.+?)\$\$$", re.DOTALL)
_DISPLAY_INLINE = re.compile(r"\$\$(?P<body>.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"\$(?P<body>[^$]+?)\$")
_TAG_DROP = re.compile(r"</?(?:b|i|em|strong|ol|ul|li|span)>", re.IGNORECASE)
_SUP = re.compile(r"<sup>(?P<body>.*?)</sup>", re.IGNORECASE | re.DOTALL)
_SUB = re.compile(r"<sub>(?P<body>.*?)</sub>", re.IGNORECASE | re.DOTALL)
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_WRAPPER_CMD = re.compile(r"\\(?:rm|text|mathrm|mathbf|mathit|mathcal|operatorname|left|right)\b")
_TAG = re.compile(r"\\tag\{[^}]*\}")
_FRAC = re.compile(r"\\frac\s*\{(?P<num>[^{}]*)\}\s*\{(?P<den>[^{}]*)\}")
_GREEK_CMD = re.compile(r"\\([A-Za-z]+)")
_SCRIPT = re.compile(r"[_^]\{?([A-Za-z0-9%,.\-+]*)\}?")
_SPACE_CMD = re.compile(r"\\[,;!:> ]|~")
_LEFTOVER_CMD = re.compile(r"\\([A-Za-z]+)")


def split_display_math(text: str) -> str | None:
    """If the whole chunk is a `$$...$$` display equation, return the inner LaTeX, else None."""
    match = _DISPLAY_MATH.fullmatch(text.strip())
    return match.group("body").strip() if match else None


def _script_repl(match: re.Match[str]) -> str:
    body = match.group(1)
    if body == "2":
        return " squared"
    if body == "3":
        return " cubed"
    return f" {body}" if body else " "


def _delatex(expr: str) -> str:
    """Turn a LaTeX fragment into plain spoken-ish tokens (best-effort, never raises)."""
    expr = _TAG.sub("", expr)
    expr = _WRAPPER_CMD.sub("", expr)
    expr = _FRAC.sub(lambda m: f"{m.group('num')} over {m.group('den')}", expr)
    for pattern, word in _OPERATORS:
        expr = re.sub(pattern, word, expr)
    # Trailing space so adjacent commands (\Delta\psi) read as "delta psi", not "deltapsi".
    expr = _GREEK_CMD.sub(lambda m: _GREEK.get(m.group(1), m.group(1)) + " ", expr)
    expr = _SCRIPT.sub(_script_repl, expr)
    expr = _SPACE_CMD.sub(" ", expr)
    expr = _LEFTOVER_CMD.sub(lambda m: m.group(1), expr)  # unknown \cmd -> cmd
    expr = expr.replace("{", " ").replace("}", " ").replace("\\", " ")
    expr = expr.replace("%", " percent")
    return " ".join(expr.split())


def clean_markup(text: str) -> str:
    """Convert inline LaTeX + HTML markup to plain text. No-op on clean (poppler) prose."""
    if "$" not in text and "<" not in text and "\\" not in text:
        return text
    text = _BR.sub(" ", text)
    text = _SUP.sub(_script_repl_html, text)
    text = _SUB.sub(lambda m: f" {m.group('body')}" if m.group("body").strip() else "", text)
    text = _TAG_DROP.sub("", text)
    # $$...$$ first (a display equation embedded mid-paragraph, not a standalone block), then
    # single-$ inline math. Both convert to plain tokens so no raw LaTeX survives.
    text = _DISPLAY_INLINE.sub(lambda m: f" {_delatex(m.group('body'))} ", text)
    text = _INLINE_MATH.sub(lambda m: f" {_delatex(m.group('body'))} ", text)
    return " ".join(text.split())


def _script_repl_html(match: re.Match[str]) -> str:
    body = match.group("body").strip()
    if body == "2":
        return " squared"
    if body == "3":
        return " cubed"
    # Bare numeric/footnote superscripts (citation markers) are dropped; short text kept.
    if not body or body.isdigit():
        return ""
    return f" {body}"
