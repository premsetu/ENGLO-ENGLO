from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path


_VOICE_EN = os.getenv("TTS_VOICE_EN", "en-IN-NeerjaNeural")
_VOICE_HI = os.getenv("TTS_VOICE_HI", "hi-IN-SwaraNeural")

# SSML prosody rate by simplicity level — slow at L0, native at L4
_RATE_BY_LEVEL = {
    "L0": "-30%",
    "L1": "-20%",
    "L2": "-10%",
    "L3": "0%",
    "L4": "+5%",
}


async def _synthesize(text: str, voice: str, rate: str, out_path: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(out_path)


def speak(
    text: str,
    language_mix: str = "en",
    simplicity_level: str = "L0",
) -> None:
    """Synthesize text and play it back through the default audio output."""
    import sounddevice as sd
    import soundfile as sf

    rate = _RATE_BY_LEVEL.get(simplicity_level, "-20%")
    # Pick voice: Hindi voice for pure Hindi, Indian-English otherwise.
    # Code-switched (hi+en) lines use the Hindi voice which handles both.
    voice = _VOICE_HI if language_mix == "hi" else _VOICE_EN

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name

    try:
        asyncio.run(_synthesize(text, voice, rate, tmp))
        data, samplerate = sf.read(tmp)
        sd.play(data, samplerate)
        sd.wait()
    finally:
        Path(tmp).unlink(missing_ok=True)
