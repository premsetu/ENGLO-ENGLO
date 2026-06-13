from __future__ import annotations

import os
from pathlib import Path

_model = None


def _load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        model_size = os.getenv("WHISPER_MODEL", "base")
        # device="cpu", compute_type="int8" keeps it lean on any machine
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str | Path) -> str:
    """Return the transcript of an audio file, accent-tolerant via Whisper."""
    model = _load_model()
    segments, _info = model.transcribe(
        str(audio_path),
        language="en",
        beam_size=5,
        # condition_on_previous_text=False keeps one-sentence turns accurate
        condition_on_previous_text=False,
    )
    return " ".join(s.text.strip() for s in segments).strip()
