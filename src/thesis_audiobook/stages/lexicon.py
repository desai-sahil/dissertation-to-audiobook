"""Stage: pronunciation-dictionary publisher.

Publishes the versioned domain alias/phoneme rules (loaded at the composition root into
ctx.pronunciation_lexicon) through the PronunciationPublisher port, then records the
returned locator on the Context so the renderer attaches it to every TTS request. A
no-op when there are no rules. The publish is mocked in tests; the cost guard fails any
accidental real publish.
"""

from __future__ import annotations

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Document
from thesis_audiobook.pronunciation import PronunciationPublishError
from thesis_audiobook.warnings import LowConfidence


class LexiconStage:
    name = "lexicon"

    def run(self, doc: Document, ctx: Context) -> Document:
        lexicon = ctx.pronunciation_lexicon
        if not lexicon.rules:
            ctx.dictionary_locators = []
            return doc
        name = f"thesis-audiobook {lexicon.version}"
        try:
            locator = ctx.pronunciation.publish(name, lexicon.rules)
        except PronunciationPublishError as error:
            # The dictionary is an optional safety net over the already-normalized script,
            # so a publish failure warns at the gate and the render proceeds without it.
            ctx.dictionary_locators = []
            ctx.warnings.add(
                LowConfidence(
                    block_id="pronunciation",
                    reason=f"dictionary publish skipped, rendering without it: {error}",
                    score=0.0,
                )
            )
            ctx.log.info("pronunciation_publish_skipped", error=str(error))
            return doc
        ctx.dictionary_locators = [locator]
        ctx.log.info("pronunciation_published", version=lexicon.version, rules=len(lexicon.rules))
        return doc
