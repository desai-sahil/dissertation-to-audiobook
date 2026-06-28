"""Render PDF pages to PNG bytes via poppler's pdftoppm. I/O at the edge (subprocess + tempfile).

This is the ground-truth source for the vision passes: the rendered page, not the lossy text
extraction. It is offline and free (no network, no LLM), so it is not behind the cost guard; it does
require poppler (`brew install poppler`), the same dependency the offline poppler parser already
uses. Kept out of the unit suite (it shells out) - the vision tests feed canned image bytes instead.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def render_pdf_pages(
    pdf_path: Path, *, dpi: int = 100, first: int | None = None, last: int | None = None
) -> list[bytes]:  # pragma: no cover - shells out to poppler; exercised via the billed runner
    """Render pages of `pdf_path` to PNG bytes, in page order. `first`/`last` (1-based, inclusive)
    limit the range. Raises CalledProcessError if pdftoppm fails (e.g. poppler missing)."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "page"
        cmd = ["pdftoppm", "-png", "-r", str(dpi)]
        if first is not None:
            cmd += ["-f", str(first)]
        if last is not None:
            cmd += ["-l", str(last)]
        cmd += [str(pdf_path), str(prefix)]
        subprocess.run(cmd, check=True, capture_output=True)
        return [p.read_bytes() for p in sorted(Path(tmp).glob("page*.png"))]
