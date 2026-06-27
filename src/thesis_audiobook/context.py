"""The Context: dependency injection for a single pipeline run.

Stages receive their ports, config, logger, and warnings sink through this object.
They never import adapters directly. `pdf_bytes` and the `rendered` / `final_audio`
scratch fields hold run-scoped state; the CLI composition root performs the actual
filesystem writes, not the stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from thesis_audiobook.config import Config
from thesis_audiobook.curate import PronunciationPlan
from thesis_audiobook.ir import StructureMap
from thesis_audiobook.lexicon import DEFAULT_LEXICON, Lexicon
from thesis_audiobook.log import StructuredLogger
from thesis_audiobook.ports.audio import AudioMuxer, NamedBlob
from thesis_audiobook.ports.bib import BibParser
from thesis_audiobook.ports.cache import Cache
from thesis_audiobook.ports.llm import LlmClient
from thesis_audiobook.ports.parser import PdfParser
from thesis_audiobook.ports.pronunciation import PronunciationPublisher
from thesis_audiobook.ports.tts import TtsClient
from thesis_audiobook.pronunciation import DictionaryLocator, PronunciationLexicon
from thesis_audiobook.provenance import ProvenanceMap
from thesis_audiobook.script_qc import ScriptQcReport
from thesis_audiobook.script_repair import AppliedRepair, RejectedRepair, ScriptRepairPlan
from thesis_audiobook.structurer import Reclassification
from thesis_audiobook.warnings import WarningsSink


def _new_byte_map() -> dict[str, bytes]:
    return {}


def _default_lexicon() -> Lexicon:
    return DEFAULT_LEXICON


def _empty_pronunciation() -> PronunciationLexicon:
    return PronunciationLexicon(version="none", rules=[])


def _new_locators() -> list[DictionaryLocator]:
    return []


def _new_blobs() -> list[NamedBlob]:
    return []


def _new_applied() -> list[AppliedRepair]:
    return []


def _new_rejected() -> list[RejectedRepair]:
    return []


def _new_reclass() -> list[Reclassification]:
    return []


@dataclass
class Context:
    config: Config
    parser: PdfParser
    bib: BibParser
    llm: LlmClient
    tts: TtsClient
    cache: Cache
    muxer: AudioMuxer
    pronunciation: PronunciationPublisher
    log: StructuredLogger
    warnings: WarningsSink
    lexicon: Lexicon = field(default_factory=_default_lexicon)
    pronunciation_lexicon: PronunciationLexicon = field(default_factory=_empty_pronunciation)
    # Run-scoped state.
    pdf_bytes: bytes = b""
    cover_image: bytes | None = None
    structure_map: StructureMap | None = None
    reclassifications: list[Reclassification] = field(default_factory=_new_reclass)
    script_qc_report: ScriptQcReport | None = None
    script_repair_plan: ScriptRepairPlan | None = None
    script_repair_applied: list[AppliedRepair] = field(default_factory=_new_applied)
    script_repair_rejected: list[RejectedRepair] = field(default_factory=_new_rejected)
    pronunciation_plan: PronunciationPlan | None = None
    dictionary_locators: list[DictionaryLocator] = field(default_factory=_new_locators)
    rendered: dict[str, bytes] = field(default_factory=_new_byte_map)
    final_audio: bytes = b""
    audio_outputs: list[NamedBlob] = field(default_factory=_new_blobs)
    provenance: ProvenanceMap | None = None
    chapter_count: int = 0
