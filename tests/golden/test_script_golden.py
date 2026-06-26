from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, Profile, committee_profile, general_profile
from thesis_audiobook.ir import Document, DocumentMeta
from thesis_audiobook.stages import build_default_pipeline


@pytest.mark.parametrize(
    "profile_factory,name",
    [(committee_profile, "committee"), (general_profile, "general")],
)
def test_full_script_golden(
    tiny_ir_path: Path,
    snapshot: SnapshotAssertion,
    profile_factory: Callable[[], Profile],
    name: str,
) -> None:
    ctx = build_mock_context(
        Config(profile=profile_factory()), pdf_bytes=b"x", mock_ir=tiny_ir_path
    )
    doc = build_default_pipeline().run(Document(meta=DocumentMeta(title="x")), ctx)
    assert doc.script == snapshot(name=name)
