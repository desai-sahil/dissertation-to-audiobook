"""Pipeline stages. Each is pure or port-mediated; none import adapters."""

from __future__ import annotations

from thesis_audiobook.pipeline import Pipeline, Stage
from thesis_audiobook.stages.appendix_signpost import AppendixSignpostStage
from thesis_audiobook.stages.assemble_audio import AssembleAudioStage
from thesis_audiobook.stages.assemble_script import AssembleScriptStage
from thesis_audiobook.stages.build_ir import BuildIrStage
from thesis_audiobook.stages.cartographer import CartographerStage
from thesis_audiobook.stages.citations import CitationsStage
from thesis_audiobook.stages.curate import CurateStage
from thesis_audiobook.stages.figures import FiguresStage
from thesis_audiobook.stages.ingest import IngestStage
from thesis_audiobook.stages.lexicon import LexiconStage
from thesis_audiobook.stages.math import MathStage
from thesis_audiobook.stages.normalize import NormalizeStage
from thesis_audiobook.stages.script_qc import ScriptQcStage
from thesis_audiobook.stages.script_repair import ScriptRepairStage
from thesis_audiobook.stages.select import SelectStage
from thesis_audiobook.stages.tts import TtsStage


def default_stages() -> list[Stage]:
    return [
        IngestStage(),
        BuildIrStage(),
        CartographerStage(),
        SelectStage(),
        CurateStage(),
        MathStage(),
        FiguresStage(),
        CitationsStage(),
        NormalizeStage(),
        AppendixSignpostStage(),
        AssembleScriptStage(),
        ScriptRepairStage(),
        ScriptQcStage(),
        LexiconStage(),
        TtsStage(),
        AssembleAudioStage(),
    ]


def build_default_pipeline() -> Pipeline:
    return Pipeline(default_stages())
