"""Generate a default audiobook cover from the template + the dissertation title/author. Edge I/O.

Renders ``meta.title`` (Newsreader serif) and ``meta.author`` (Space Mono, letter-tracked) onto the
generic cover template, after auto-cleaning the rasterized ``<Dissertation Title>`` / ``<AUTHOR
NAME>`` placeholders (the background is a flat green, so we just repaint those two regions). Called
by the CLI when no ``--cover`` is provided. Deterministic: same title+author -> same PNG bytes.

All geometry is measured from ``cover/cover - generic.png`` (3000x3000) and expressed as canvas
fractions, so a differently-sized template still lays out correctly. See the cover decision memo.
"""

from __future__ import annotations

from importlib import resources
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

_REF = 3000.0  # the template the geometry below was measured against

# colors (sampled from the template)
_CREAM = (242, 239, 231)
_SAGE = (135, 164, 139)

# title block, as canvas fractions: left-anchored, fits within the content column
_TITLE_LEFT = 270 / _REF
_TITLE_TOP = 600 / _REF  # cap-top of the first line
_CONTENT_RIGHT = 2750 / _REF
_TITLE_CAP = 188 / _REF  # single-line cap height (the design size); long titles shrink from here
_TITLE_BUDGET_BOTTOM = 2360 / _REF  # the block may grow down to here (clear of the lower rule)
_LINE_SPACING = 1.1

# author label: right-anchored monospace, all-caps, letter-tracked
_AUTHOR_RIGHT = 2735 / _REF
_AUTHOR_BASELINE = 2729 / _REF
_AUTHOR_CAP = 40 / _REF
_AUTHOR_TRACK = 0.22  # extra advance per glyph, in em (matches the template's wide tracking)

# regions repainted over the rasterized placeholders (generous; both sit clear of the rules)
_TITLE_CLEAR = (235 / _REF, 535 / _REF, 2800 / _REF, 905 / _REF)
_AUTHOR_CLEAR = (1900 / _REF, 2650 / _REF, 2800 / _REF, 2775 / _REF)


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    ref = resources.files("thesis_audiobook") / "assets" / "fonts" / name
    with resources.as_file(ref) as path:
        return ImageFont.truetype(str(path), size)


def _num(value: object, fallback: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else fallback


def _set_axes(font: ImageFont.FreeTypeFont, *, opsz: float | None, wght: float | None) -> None:
    """Pin a variable font's optical-size (to max, for display) and weight axes; no-op if static."""
    try:
        axes = font.get_variation_axes()
    except OSError:
        return
    if not axes:
        return
    values: list[float] = []
    for axis in axes:
        raw = axis.get("name", "")
        label = raw.decode() if isinstance(raw, bytes) else str(raw)
        low = label.lower()
        default = _num(axis.get("default"))
        if "optical" in low or low == "opsz":
            values.append(_num(axis.get("maximum"), default) if opsz is None else opsz)
        elif "weight" in low or low == "wght":
            values.append(default if wght is None else wght)
        else:
            values.append(default)
    font.set_variation_by_axes(values)


def _cap_height(font: ImageFont.FreeTypeFont) -> int:
    box = font.getbbox("H")
    return int(box[3] - box[1])


def _serif(size: int) -> ImageFont.FreeTypeFont:
    font = _load_font("Newsreader.ttf", size)
    _set_axes(font, opsz=None, wght=440)  # opsz=None -> max (display cut); medium weight
    return font


def _serif_for_cap(target_px: int) -> ImageFont.FreeTypeFont:
    """A Newsreader instance whose capital height is ~target_px (binary search on point size)."""
    lo, hi = 8, max(16, target_px * 3)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _cap_height(_serif(mid)) <= target_px:
            lo = mid
        else:
            hi = mid - 1
    return _serif(lo)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.getlength(trial) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit_title(
    title: str, max_w: float, budget_h: float, cap_px: int
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """Largest Newsreader size (capped at the design cap height) that wraps `title` within the
    content width and the vertical budget. Returns (font, wrapped lines, line height)."""
    font = _serif_for_cap(cap_px)
    while True:
        lines = _wrap(title, font, max_w)
        line_h = int(font.size * _LINE_SPACING)
        too_tall = len(lines) * line_h > budget_h
        too_wide = any(font.getlength(line) > max_w for line in lines)
        if (not too_tall and not too_wide) or font.size <= 24:
            return font, lines, line_h
        font = _serif(int(font.size * 0.92))


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    *,
    right: float,
    baseline: float,
    track_em: float,
    fill: tuple[int, int, int],
) -> None:
    """Right-anchored, letter-tracked run (monospace caps), drawn glyph by glyph."""
    track = track_em * font.size
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + track * (len(text) - 1 if text else 0)
    x = right - total
    for ch, width in zip(text, widths, strict=True):
        draw.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
        x += width + track


def generate_cover(title: str, author: str | None, *, template: bytes) -> bytes:
    """Render `title` and `author` onto the cover `template` (PNG bytes), returning PNG bytes."""
    img = Image.open(BytesIO(template)).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    bg = img.getpixel((max(2, w // 200), max(2, h // 200)))

    # erase the rasterized placeholders by repainting their regions with the flat background
    for x0, y0, x1, y1 in (_TITLE_CLEAR, _AUTHOR_CLEAR):
        draw.rectangle((x0 * w, y0 * h, x1 * w, y1 * h), fill=bg)

    # title (serif, cream, left-anchored, size-to-fit)
    max_w = (_CONTENT_RIGHT - _TITLE_LEFT) * w
    budget_h = (_TITLE_BUDGET_BOTTOM - _TITLE_TOP) * h
    font, lines, line_h = _fit_title(title.strip(), max_w, budget_h, round(_TITLE_CAP * h))
    y = _TITLE_TOP * h
    for line in lines:
        draw.text((_TITLE_LEFT * w, y), line, font=font, fill=_CREAM, anchor="la")
        y += line_h

    # author (monospace caps, sage, right-anchored, tracked)
    if author and author.strip():
        afont = _load_font("SpaceMono-Regular.ttf", _mono_size_for_cap(round(_AUTHOR_CAP * h)))
        _draw_tracked(
            draw,
            author.strip().upper(),
            afont,
            right=_AUTHOR_RIGHT * w,
            baseline=_AUTHOR_BASELINE * h,
            track_em=_AUTHOR_TRACK,
            fill=_SAGE,
        )

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _mono_size_for_cap(target_px: int) -> int:
    lo, hi = 8, max(16, target_px * 3)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _cap_height(_load_font("SpaceMono-Regular.ttf", mid)) <= target_px:
            lo = mid
        else:
            hi = mid - 1
    return lo
