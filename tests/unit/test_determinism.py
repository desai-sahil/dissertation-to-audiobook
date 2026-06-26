from __future__ import annotations

from pathlib import Path

from thesis_audiobook.bootstrap import build_mock_context
from thesis_audiobook.config import Config, committee_profile, general_profile
from thesis_audiobook.ir import Document, DocumentMeta
from thesis_audiobook.stages import build_default_pipeline


def _script(profile_name: str, tiny_ir_path: Path) -> str | None:
    profile = committee_profile() if profile_name == "committee" else general_profile()
    ctx = build_mock_context(Config(profile=profile), pdf_bytes=b"x", mock_ir=tiny_ir_path)
    return build_default_pipeline().run(Document(meta=DocumentMeta(title="x")), ctx).script


def test_same_input_same_spoken_output(tiny_ir_path: Path) -> None:
    # MockLlm is keyed by input hash, so glosses/summaries are reproducible.
    assert _script("committee", tiny_ir_path) == _script("committee", tiny_ir_path)
    assert _script("general", tiny_ir_path) == _script("general", tiny_ir_path)


def test_profiles_produce_different_scripts(tiny_ir_path: Path) -> None:
    # Determinism must not mean profile-insensitivity: committee (gloss/summarize/brief
    # citations) and general (announce/skip/drop) voice the same IR differently.
    assert _script("committee", tiny_ir_path) != _script("general", tiny_ir_path)
