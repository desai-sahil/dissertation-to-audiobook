"""Convert Marker's LaTeX + HTML markup into plain, spoken-friendly text. Pure, no I/O.

Marker renders math as LaTeX ($$...$$ display, $...$ inline) and uses <sup>/<sub>/<br>
markup; poppler produces none of this, so clean_markup is a no-op on clean prose and is
safe to run parser-agnostically. Display equations are detected separately
(split_display_math) and routed to the math stage; this module turns INLINE math and
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
    (r"\\frac", " the fraction "),  # fallback for a nested \frac that _FRAC could not split
]
# HTML entities and OCR-garbled comparison glyphs -> spoken words. The inverted marks (¡ ¿)
# are how this thesis's OCR rendered "<" / ">"; they never occur in normal English prose.
_ENTITY = {
    "&gt;": " greater than ",
    "&lt;": " less than ",
    "&ge;": " greater than or equal to ",
    "&le;": " less than or equal to ",
    "&ne;": " not equal to ",
    "&times;": " times ",
    "&minus;": " minus ",
    "&plusmn;": " plus or minus ",
    "&deg;": " degrees ",
    "&amp;": " and ",
    "&nbsp;": " ",
    "¡": " less than ",
    "¿": " greater than ",
}
_ENTITY_RE = re.compile("|".join(re.escape(key) for key in _ENTITY))
# Literal unicode math glyphs that Marker OCRs straight into the prose (outside $...$), so the
# LaTeX passes never see them. Mapped to spoken words; a no-op on clean English, which has none.
_UNICODE_MATH = {
    "⟨": " ",  # ⟨ angle bracket: dropped (context carries "average of")
    "⟩": " ",  # ⟩
    "∆": " delta ",  # ∆ increment
    "∇": " del ",  # ∇ nabla
    "∂": " partial ",  # ∂
    "∼": " approximately ",  # ∼
    "≈": " approximately ",  # ≈
    "≃": " approximately ",  # ≃
    "≅": " approximately ",  # ≅
    "≡": " defined as ",  # ≡
    "≪": " much less than ",  # ≪
    "≫": " much greater than ",  # ≫
    "≤": " less than or equal to ",  # ≤
    "≥": " greater than or equal to ",  # ≥
    "≲": " less than or approximately ",  # ≲
    "≳": " greater than or approximately ",  # ≳
    "≠": " not equal to ",  # ≠
    "∝": " proportional to ",  # ∝
    "±": " plus or minus ",  # ±
    "×": " times ",  # ×
    "−": " minus ",  # − (U+2212, not ASCII hyphen)
    "→": " approaches ",  # →
    "∞": " infinity ",  # ∞
    "◦": " degrees ",  # ◦ (OCR degree)
    "°": " degrees ",  # °
    "º": " degrees ",  # º
    "√": " square root ",  # √
    "∑": " sum ",  # ∑
    "∫": " integral ",  # ∫
}
_UNICODE_TABLE = str.maketrans(_UNICODE_MATH)
# Any of these characters means the text needs cleaning; without one, clean_markup is a no-op.
_MARKUP_TRIGGER = "$<\\*&¡¿" + "".join(_UNICODE_MATH)
# Markdown emphasis: **bold** / *italic*. Stripped so the markers are not voiced as "asterisk".
_EMPH = re.compile(r"\*\*(?P<b>.+?)\*\*|\*(?P<i>[^*\n]+?)\*", re.DOTALL)
# A LaTeX environment wrapper (e.g. \begin{bmatrix} ... \end{bmatrix}); drop the markers.
_ENV = re.compile(r"\\(?:begin|end)\{[^}]*\}")
_DISPLAY_MATH = re.compile(r"^\$\$(?P<body>.+?)\$\$$", re.DOTALL)
_DISPLAY_INLINE = re.compile(r"\$\$(?P<body>.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"\$(?P<body>[^$]+?)\$")
_TAG_DROP = re.compile(r"</?(?:b|i|em|strong|ol|ul|li|span)>", re.IGNORECASE)
# Capture the char before <sup> so a superscript ATTACHED TO A NUMBER (exponent or a
# Marker-fragmented decimal like "8.<sup>314</sup>") is kept, while one after a word (a
# citation marker) is dropped. Without this, "8.314" -> "8." and "10^5" -> "10".
_SUP = re.compile(r"(?P<pre>[0-9.]?)<sup>(?P<body>.*?)</sup>", re.IGNORECASE | re.DOTALL)
# Chemical formulas Marker mis-typesets with a superscript where the digit is really a
# subscript ("CO<sup>2</sup>" -> "CO squared"). Fix the few unambiguous gas-exchange molecules
# before the generic superscript handler so they read as the formula (then the lexicon spells
# "CO2" as "C O two"). Unit exponents like "m<sup>2</sup>" -> "m squared" are untouched.
_CHEM_SUP = [
    (re.compile(r"\bH<sup>2</sup>O<sup>2</sup>", re.IGNORECASE), "H2O2"),
    (re.compile(r"\bH<sup>2</sup>O\b", re.IGNORECASE), "H2O"),
    (re.compile(r"\bCO<sup>2</sup>", re.IGNORECASE), "CO2"),
    (re.compile(r"\bO<sup>2</sup>", re.IGNORECASE), "O2"),
]
_SUB = re.compile(r"<sub>(?P<body>.*?)</sub>", re.IGNORECASE | re.DOTALL)
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_WRAPPER_CMD = re.compile(r"\\(?:rm|text|mathrm|mathbf|mathit|mathcal|operatorname|left|right)\b")
_TAG = re.compile(r"\\tag\{[^}]*\}")
_FRAC = re.compile(
    r"\\frac\s*\{(?P<num>(?:[^{}]|\{[^{}]*\})*)\}\s*\{(?P<den>(?:[^{}]|\{[^{}]*\})*)\}"
)
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
    expr = _ENV.sub(" ", expr)  # drop \begin{bmatrix}/\end{bmatrix} environment markers
    expr = expr.replace("&", " ")  # matrix/table column separators
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
    """Convert inline LaTeX, HTML markup, and markdown emphasis to plain text. No-op on clean
    (poppler) prose."""
    if not any(ch in text for ch in _MARKUP_TRIGGER):
        return text
    text = _BR.sub(" ", text)
    for chem, plain in _CHEM_SUP:
        text = chem.sub(plain, text)
    text = _SUP.sub(_script_repl_html, text)
    text = _SUB.sub(lambda m: f" {m.group('body')}" if m.group("body").strip() else "", text)
    text = _TAG_DROP.sub("", text)
    # Entities AFTER <sup>/<sub>: Marker can split ">" as "<sup>&</sup>gt;", which the sup
    # handler reassembles into "&gt;"; convert those (and the OCR ¡/¿ marks) to words here.
    text = _ENTITY_RE.sub(lambda m: _ENTITY[m.group(0)], text)
    # $$...$$ first (a display equation embedded mid-paragraph, not a standalone block), then
    # single-$ inline math. Both convert to plain tokens so no raw LaTeX survives.
    text = _DISPLAY_INLINE.sub(lambda m: f" {_delatex(m.group('body'))} ", text)
    text = _INLINE_MATH.sub(lambda m: f" {_delatex(m.group('body'))} ", text)
    # Markdown emphasis: keep the content, drop the markers. Any leftover '*' (an unpaired or
    # stray marker) becomes a space, so it is never voiced as the word "asterisk".
    text = _EMPH.sub(lambda m: m.group("b") or m.group("i") or "", text)
    text = text.replace("*", " ")
    # Literal unicode math glyphs (and OCR degree marks) left in the prose -> spoken words.
    text = text.translate(_UNICODE_TABLE)
    return " ".join(text.split())


def _script_repl_html(match: re.Match[str]) -> str:
    pre = match.group("pre")
    body = match.group("body").strip()
    # Superscript fused to a number: a Marker-split decimal ("8.<sup>314</sup>" -> "8.314") or an
    # exponent ("10<sup>5</sup>" -> "10 to the power of 5").
    if pre and (pre == "." or pre.isdigit()):
        if not body:
            return pre
        if pre == "." and body.isdigit():
            return f"{pre}{body}"
        if all(ch in "+-−.0123456789" for ch in body):
            signed = body.replace("−", " minus ").replace("+", " plus ")
            return f"{pre} to the power of {signed}"
        return f"{pre} {body}"
    # pre is empty: classify by the (unconsumed) character before the tag.
    before = match.string[match.start() - 1] if match.start() > 0 else ""
    if not body:
        return ""
    if before.isalpha():
        # Attached to a word: a unit exponent (m<sup>2</sup> -> "m squared") or, for a bare
        # number, a footnote/citation marker to drop ("shown<sup>12</sup>" -> "shown").
        if body == "2":
            return " squared"
        if body == "3":
            return " cubed"
        return "" if body.isdigit() else f" {body}"
    # Standalone (space/operator/start before): Marker shredded an equation into per-character
    # <sup> tags, so this digit/symbol is a real value - keep it. Dropping it as a citation
    # marker silently garbled measurements ("8.314" -> ".314", "= 0 Pa" -> "= Pa").
    return f" {body}"
