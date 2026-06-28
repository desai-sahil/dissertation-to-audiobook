from __future__ import annotations

from thesis_audiobook.config import (
    committee_profile,
    general_profile,
    load_profile,
    profile_for,
)


def test_toml_profiles_match_code_defaults() -> None:
    # The data files are the editable source; they must mirror the code-level defaults.
    assert load_profile("committee") == committee_profile()
    assert load_profile("general") == general_profile()


def test_unknown_profile_falls_back_to_code_default() -> None:
    assert load_profile("does-not-exist") == committee_profile()


def test_profile_for_loads_from_toml() -> None:
    assert profile_for("general").equation_tier == "announce"
    assert profile_for("committee").table_handling == "summarize"
