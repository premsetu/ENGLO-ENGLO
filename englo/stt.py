from __future__ import annotations

import os
from pathlib import Path

from .models import STTResult, WordInfo

_model = None


def _load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        model_size = os.getenv("WHISPER_MODEL", "base")
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe_full(audio_path: str | Path) -> STTResult:
    """Transcribe audio and return word-level probabilities for pronunciation scoring."""
    model = _load_model()
    segments, _info = model.transcribe(
        str(audio_path),
        language="en",
        beam_size=5,
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    words: list[WordInfo] = []
    text_parts: list[str] = []

    for seg in segments:
        text_parts.append(seg.text.strip())
        if seg.words:
            for w in seg.words:
                # faster-whisper gives log-probability; convert to 0-1
                prob = max(0.0, min(1.0, float(w.probability)))
                words.append(WordInfo(
                    word=w.word.strip(),
                    probability=prob,
                    start=w.start,
                    end=w.end,
                ))

    return STTResult(transcript=" ".join(text_parts).strip(), words=words)


def transcribe(audio_path: str | Path) -> str:
    """Convenience wrapper — returns plain transcript string."""
    return transcribe_full(audio_path).transcript
