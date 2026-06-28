from __future__ import annotations

from io import BytesIO

from PIL import Image

from thesis_audiobook.adapters.cover import generate_cover

_BG = (27, 36, 31)


def _template(size: int = 900) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (size, size), _BG).save(buf, format="PNG")
    return buf.getvalue()


def _open(png: bytes) -> Image.Image:
    return Image.open(BytesIO(png)).convert("RGB")


def _count_near(img: Image.Image, box: tuple[int, int, int, int], rgb: tuple[int, int, int]) -> int:
    raw = img.crop(box).tobytes()
    pixels = (raw[i : i + 3] for i in range(0, len(raw), 3))
    return sum(1 for p in pixels if all(abs(p[i] - rgb[i]) <= 45 for i in range(3)))


def test_returns_valid_png_of_same_size() -> None:
    png = generate_cover("A Short Thesis Title", "Jane Doe", template=_template(900))
    img = _open(png)
    assert img.size == (900, 900)


def test_is_deterministic() -> None:
    a = generate_cover("A Title", "Jane Doe", template=_template())
    b = generate_cover("A Title", "Jane Doe", template=_template())
    assert a == b


def test_title_is_rendered_in_cream() -> None:
    blank = _open(_template())
    cover = _open(generate_cover("Water Stress Sensing", "Jane Doe", template=_template()))
    title_box = (0, 150, 900, 600)  # upper title band
    cream = (242, 239, 231)
    assert _count_near(blank, title_box, cream) == 0  # blank template has no cream there
    assert _count_near(cover, title_box, cream) > 500  # the title painted cream glyphs in


def test_author_is_rendered_in_sage_bottom_right() -> None:
    cover = _open(generate_cover("A Title", "Piyush Jain", template=_template()))
    author_box = (450, 780, 900, 870)  # bottom-right region
    assert _count_near(cover, author_box, (135, 164, 139)) > 100


def test_no_author_leaves_label_blank() -> None:
    cover = _open(generate_cover("A Title", None, template=_template()))
    author_box = (450, 780, 900, 870)
    assert _count_near(cover, author_box, (135, 164, 139)) == 0


def test_very_long_title_still_fits_and_renders() -> None:
    long_title = (
        "Transducing thermodynamic state of water into optical signatures: "
        "applications in synthetic materials and living systems"
    )
    img = _open(generate_cover(long_title, "Piyush Jain", template=_template()))
    assert img.size == (900, 900)
    # the title must not spill into the bottom author rule zone
    assert _count_near(img, (0, 760, 900, 780), (242, 239, 231)) == 0
