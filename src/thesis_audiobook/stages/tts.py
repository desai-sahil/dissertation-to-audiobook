"""Stage: TTS renderer.

Port-mediated. Builds a fully specified TtsRequest per chunk (voice, model, settings,
seed, pronunciation locators, and neighbor text for prosody continuity), then renders
through the TtsClient port with a content-addressed cache in front. The cache key pins
every field that changes the audio bytes - including the neighbor text, per the spec
section 10 decision to refresh a seam when its neighbor is edited - so an unchanged
chunk is served from cache and only edited chunks (and their immediate seams) re-render.

apply_text_normalization defaults to "off": M1 already normalized the script, so letting
ElevenLabs normalize again would risk re-mangling it. Flip it via the profile for raw
scripts. The stage does no filesystem I/O; rendered bytes are stashed on the Context.
"""

from __future__ import annotations

import hashlib
import json

from thesis_audiobook.context import Context
from thesis_audiobook.ir import Chunk, Document
from thesis_audiobook.ports.tts import TtsRequest


def chunk_cache_key(req: TtsRequest, dict_version: str) -> str:
    # Deliberately excluded from the key: the pronunciation locators (a rules change
    # bumps dict_version, which IS keyed; the API-assigned version id is non-deterministic
    # so keying it would defeat the cache), and previous/next_request_ids (the renderer
    # stitches via neighbor text and never populates them - pinned by the renderer tests -
    # and request ids are per-call, so keying them would also defeat the cache).
    payload = json.dumps(
        {
            "text": req.text,
            "voice_id": req.voice_id,
            "model_id": req.model_id,
            "voice_settings": req.voice_settings.model_dump(),
            "output_format": req.output_format,
            "apply_text_normalization": req.apply_text_normalization,
            "seed": req.seed,
            "previous_text": req.previous_text,
            "next_text": req.next_text,
            "dict_version": dict_version,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TtsStage:
    name = "tts"

    def run(self, doc: Document, ctx: Context) -> Document:
        config = ctx.config
        profile = config.profile
        by_id: dict[str, Chunk] = {chunk.id: chunk for chunk in doc.chunks}
        dict_version = ctx.pronunciation_lexicon.version
        hits = 0

        for chunk in doc.chunks:
            prev_text = by_id[chunk.prev_id].text if chunk.prev_id in by_id else None
            next_text = by_id[chunk.next_id].text if chunk.next_id in by_id else None
            request = TtsRequest(
                text=chunk.text,
                voice_id=profile.voice_id,
                model_id=profile.model_id,
                voice_settings=profile.voice_settings,
                output_format=profile.output_format,
                apply_text_normalization=profile.apply_text_normalization,
                seed=config.seed,
                previous_text=prev_text,
                next_text=next_text,
                locators=ctx.dictionary_locators,
            )
            key = chunk_cache_key(request, dict_version)
            cached = ctx.cache.get(key)
            if cached is None:
                audio = ctx.tts.synthesize(request)
                ctx.cache.put(key, audio)
            else:
                audio = cached
                hits += 1
            ctx.rendered[chunk.id] = audio

        ctx.log.info("tts_rendered", chunks=len(doc.chunks), cache_hits=hits)
        return doc
