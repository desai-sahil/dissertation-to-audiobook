"""Pure audio helpers: deterministic silent-WAV synthesis and WAV duration. No I/O.

The mock TTS uses silent_wav so test audio duration is a deterministic function of
input length, and the pure mock muxer reads durations back with wav_duration. Real
M4B muxing via ffmpeg lives in the FfmpegMuxer adapter.
"""

from __future__ import annotations

import struct

_SAMPLE_RATE = 22_050
_BITS_PER_SAMPLE = 16
_NUM_CHANNELS = 1


def silent_wav(seconds: float) -> bytes:
    """Return a valid mono 16-bit PCM WAV of `seconds` of silence."""
    n_samples = max(1, int(seconds * _SAMPLE_RATE))
    data = b"\x00\x00" * n_samples
    byte_rate = _SAMPLE_RATE * _NUM_CHANNELS * (_BITS_PER_SAMPLE // 8)
    block_align = _NUM_CHANNELS * (_BITS_PER_SAMPLE // 8)
    fmt_chunk = struct.pack(
        "<4sIHHIIHH",
        b"fmt ",
        16,
        1,  # PCM
        _NUM_CHANNELS,
        _SAMPLE_RATE,
        byte_rate,
        block_align,
        _BITS_PER_SAMPLE,
    )
    data_chunk = struct.pack("<4sI", b"data", len(data)) + data
    riff_size = 4 + len(fmt_chunk) + len(data_chunk)
    header = struct.pack("<4sI4s", b"RIFF", riff_size, b"WAVE")
    return header + fmt_chunk + data_chunk


class NotAWavError(ValueError):
    """The bytes are not a parseable RIFF/WAVE stream."""


def wav_duration(data: bytes) -> float:
    """Pure: seconds of audio in a PCM WAV, from its `fmt ` byte rate and `data` size.

    Used by the pure mock muxer to time chunks offline. The real ffmpeg path uses
    ffprobe instead, since ElevenLabs returns MP3, not WAV.
    """
    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise NotAWavError("not a RIFF/WAVE stream")
    byte_rate: int | None = None
    data_size: int | None = None
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        (chunk_size,) = struct.unpack_from("<I", data, pos + 4)
        body = pos + 8
        if chunk_id == b"fmt " and body + 16 <= len(data):
            (byte_rate,) = struct.unpack_from("<I", data, body + 8)
        elif chunk_id == b"data":
            data_size = chunk_size
        pos = body + chunk_size + (chunk_size & 1)  # chunks are word-aligned
    if not byte_rate or data_size is None:
        raise NotAWavError("missing fmt byte rate or data chunk")
    return data_size / byte_rate
