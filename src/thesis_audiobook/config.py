"""Typed configuration and listener profiles.

Profiles are data, not code branches: each ships as a validated TOML file under
data/profiles/, loaded by profile_for(). The committee_profile()/general_profile()
constructors remain as code-level fallbacks (and the source of truth the TOML mirrors).
Secrets never live here; API keys come from the environment in the real adapters.
"""

from __future__ import annotations

import importlib.resources
import tomllib
from typing import Literal

from pydantic import Field

from thesis_audiobook.ir import StrictModel

ParserBackend = Literal["marker", "mineru", "poppler", "markdown"]
# m4b and mp4 are the same MPEG-4/AAC container (chaptered single file); mp3 is one
# file per chapter. m4b signals "audiobook" to Apple Books; mp4 plays everywhere.
OutputMode = Literal["m4b", "mp4", "mp3"]
TextNormalization = Literal["auto", "on", "off"]


class VoiceSettings(StrictModel):
    """ElevenLabs voice settings. Part of the TTS cache key, so a change re-renders."""

    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True
    speed: float = 1.0


class Profile(StrictModel):
    name: str = "committee"
    equation_tier: Literal["announce", "full"] = "announce"
    citation_policy: Literal["drop", "brief", "full"] = "brief"
    table_handling: Literal["skip", "summarize"] = "summarize"
    include_appendices: bool = False
    voice_id: str = "mock-voice"
    # eleven_multilingual_v2 for the deliverable; preview_model_id (flash) for cheap previews.
    model_id: str = "eleven_multilingual_v2"
    preview_model_id: str = "eleven_flash_v2_5"
    voice_settings: VoiceSettings = Field(default_factory=VoiceSettings)
    output_format: str = "mp3_44100_128"
    # M1 already normalized the script, so ElevenLabs normalization defaults off. The
    # "off" choice is documented in stages/tts.py; flip via config for raw scripts.
    apply_text_normalization: TextNormalization = "off"


def committee_profile() -> Profile:
    return Profile(
        name="committee",
        equation_tier="announce",
        citation_policy="brief",
        table_handling="summarize",
        include_appendices=False,
    )


def general_profile() -> Profile:
    return Profile(
        name="general",
        equation_tier="announce",
        citation_policy="drop",
        table_handling="skip",
        include_appendices=False,
    )


def load_profile(name: str) -> Profile:
    """Load and validate a profile from data/profiles/<name>.toml.

    Falls back to the code-level default if the file is missing, so the pipeline always
    has a valid profile even without the data files. Editing the TOML retunes a profile
    without touching code.
    """
    fallback = general_profile() if name == "general" else committee_profile()
    try:
        text = (
            importlib.resources.files("thesis_audiobook")
            .joinpath(f"data/profiles/{name}.toml")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError):
        return fallback
    return Profile.model_validate(tomllib.loads(text))


def profile_for(name: str) -> Profile:
    return load_profile(name)


class Config(StrictModel):
    profile: Profile = Field(default_factory=committee_profile)
    seed: int = 0
    # Pinned placeholder rate for the dry-run cost estimate. This is NOT live
    # ElevenLabs pricing; set it from your plan's per-character rate.
    usd_per_character: float = 0.00003
    output_dir: str = "out"
    chunk_char_limit: int = 2000
    # LLM pronunciation curator (per-document). On by default; --no-curate disables it.
    curate: bool = True
    # LLM thesis cartographer (structure map: include/skip regions). On by default;
    # --no-structure-eval disables it (then the build_ir heuristics stand alone).
    structure_eval: bool = True
    # Guarded auto-repair of the script (applies only safe pronunciation fixes, before the
    # phase-4 QC gate re-audits). On by default; --no-script-repair disables it.
    script_repair: bool = True
    # Phase-4 pre-TTS script QC (red-flag check before ElevenLabs). On by default.
    script_qc: bool = True
    # Audio assembly: a single M4B with chapter markers, or flat per-chapter MP3s.
    output_mode: OutputMode = "m4b"
    narrator: str = "Audiobook narrator"
    # Where the FileCache stores content-addressed chunk audio across runs.
    cache_dir: str = ".cache/tts"
    # Parsing backend. Marker is the spec's primary parser; MinerU is the
    # equation-heavy alternative; poppler is the pure-Python offline fallback.
    parser_backend: ParserBackend = "marker"
    # Path to a pre-parsed markdown file, used when parser_backend == "markdown" (run a
    # standalone Marker/MinerU to produce it; see adapters/markdown_parser.py).
    markdown_path: str | None = None
    grobid_url: str = "http://localhost:8070"
