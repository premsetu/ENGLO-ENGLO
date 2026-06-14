"""Text-to-speech with bilingual stitching.

Single voice for pure-language lines; per-segment voice routing + numpy
concatenation for code-switched (hi+en) lines.  Backed by edge-tts
(Microsoft neural voices, free, no API key, requires network).

Public surface:
  speak(text, language_mix, simplicity_level)  — synthesize + play (CLI)
  synthesize(text, language_mix, simplicity_level) -> bytes  — MP3 bytes (API)
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
from pathlib import Path

import numpy as np

from .bilingual import split_segments

_VOICE_EN = os.getenv("TTS_VOICE_EN", "en-IN-NeerjaNeural")
_VOICE_HI = os.getenv("TTS_VOICE_HI", "hi-IN-SwaraNeural")

_RATE_BY_LEVEL: dict[str, str] = {
    "L0": "-30%",
    "L1": "-20%",
    "L2": "-10%",
    "L3": "0%",
    "L4": "+5%",
}


def _segments(text: str, language_mix: str) -> list[tuple[str, str]]:
    if language_mix == "hi+en":
        return split_segments(text)
    if language_mix == "hi":
        return [(text, "hi")]
    return [(text, "en")]


async def _mp3_bytes(text: str, voice: str, rate: str) -> bytes:
    """Synthesize one segment to raw MP3 bytes."""
    import edge_tts
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def _array_and_rate(text: str, voice: str, rate: str) -> tuple[np.ndarray, int]:
    """Synthesize one segment to a numpy float32 array."""
    import soundfile as sf
    mp3 = await _mp3_bytes(text, voice, rate)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(mp3)
        tmp = f.name
    try:
        data, sr = sf.read(tmp, always_2d=False)
        return data, sr
    finally:
        Path(tmp).unlink(missing_ok=True)


async def _synthesize_async(text: str, language_mix: str, rate: str) -> bytes:
    """Return combined MP3 bytes for all segments (stitched for hi+en)."""
    segs = _segments(text, language_mix)
    parts: list[bytes] = []
    for seg_text, lang in segs:
        if not seg_text.strip():
            continue
        voice = _VOICE_HI if lang == "hi" else _VOICE_EN
        parts.append(await _mp3_bytes(seg_text, voice, rate))
    # Concatenate raw MP3 frames — decoders handle this correctly
    return b"".join(parts)


async def _speak_async(text: str, language_mix: str, rate: str) -> None:
    import soundfile as sf
    import sounddevice as sd

    segs = _segments(text, language_mix)
    arrays: list[np.ndarray] = []
    sample_rate = 24_000

    for seg_text, lang in segs:
        if not seg_text.strip():
            continue
        voice = _VOICE_HI if lang == "hi" else _VOICE_EN
        data, sr = await _array_and_rate(seg_text, voice, rate)
        sample_rate = sr
        if arrays and data.ndim != arrays[-1].ndim:
            data = data.reshape(-1) if arrays[-1].ndim == 1 else data.reshape(-1, 1)
        arrays.append(data)

    if not arrays:
        return
    combined = np.concatenate(arrays, axis=0)
    sd.play(combined, sample_rate)
    sd.wait()


# ── Public API ────────────────────────────────────────────────────────────────

def speak(text: str, language_mix: str = "en", simplicity_level: str = "L0") -> None:
    """Synthesize and play through the default audio output (CLI use)."""
    rate = _RATE_BY_LEVEL.get(simplicity_level, "-20%")
    asyncio.run(_speak_async(text, language_mix, rate))


def synthesize(text: str, language_mix: str = "en", simplicity_level: str = "L0") -> bytes:
    """Return MP3 bytes without playing — for API/mobile use."""
    rate = _RATE_BY_LEVEL.get(simplicity_level, "-20%")
    return asyncio.run(_synthesize_async(text, language_mix, rate))
