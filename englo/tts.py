"""Text-to-speech with bilingual stitching.

Single voice for pure-language lines; per-segment voice routing + numpy
concatenation for code-switched (hi+en) lines.  Backed by edge-tts
(Microsoft neural voices, free, no API key, requires network).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import numpy as np

from .bilingual import split_segments

_VOICE_EN = os.getenv("TTS_VOICE_EN", "en-IN-NeerjaNeural")
_VOICE_HI = os.getenv("TTS_VOICE_HI", "hi-IN-SwaraNeural")

# SSML prosody rate by simplicity level (spec §7: slow+clear at L0 → native at L4)
_RATE_BY_LEVEL: dict[str, str] = {
    "L0": "-30%",
    "L1": "-20%",
    "L2": "-10%",
    "L3": "0%",
    "L4": "+5%",
}


async def _synthesize_to_array(text: str, voice: str, rate: str) -> tuple[np.ndarray, int]:
    """Synthesize one text segment; return (audio_array, sample_rate)."""
    import soundfile as sf
    import edge_tts

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(tmp)
        data, samplerate = sf.read(tmp, always_2d=False)
        return data, samplerate
    finally:
        Path(tmp).unlink(missing_ok=True)


async def _speak_async(text: str, language_mix: str, rate: str) -> None:
    import sounddevice as sd

    # Determine segments: split on Devanagari boundaries for mixed lines
    if language_mix == "hi+en":
        segments = split_segments(text)
    elif language_mix == "hi":
        segments = [(text, "hi")]
    else:
        segments = [(text, "en")]

    arrays: list[np.ndarray] = []
    sample_rate = 24_000  # edge-tts default; overwritten by first real segment

    for seg_text, lang in segments:
        if not seg_text.strip():
            continue
        voice = _VOICE_HI if lang == "hi" else _VOICE_EN
        data, sr = await _synthesize_to_array(seg_text, voice, rate)
        sample_rate = sr

        # Match channel count across segments (edge-tts returns mono; keep as-is)
        if arrays and data.ndim != arrays[-1].ndim:
            data = data.reshape(-1) if arrays[-1].ndim == 1 else data.reshape(-1, 1)
        arrays.append(data)

    if not arrays:
        return

    combined = np.concatenate(arrays, axis=0)
    sd.play(combined, sample_rate)
    sd.wait()


def speak(
    text: str,
    language_mix: str = "en",
    simplicity_level: str = "L0",
) -> None:
    """Synthesize and play text with the appropriate voice(s) for the given level."""
    rate = _RATE_BY_LEVEL.get(simplicity_level, "-20%")
    asyncio.run(_speak_async(text, language_mix, rate))
