from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path


_RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "7"))
_SAMPLE_RATE = 16_000  # Whisper expects 16 kHz


def record_to_file() -> str:
    """Record from the default microphone until Enter is pressed (max RECORD_SECONDS).

    Returns the path to a temporary WAV file — caller must delete it.
    """
    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    frames: list[np.ndarray] = []
    stop_event = threading.Event()

    def _callback(indata: np.ndarray, frame_count: int, time_info, status) -> None:
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=_SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=_callback,
    )

    def _wait_for_enter():
        input()
        stop_event.set()

    t = threading.Thread(target=_wait_for_enter, daemon=True)
    t.start()

    with stream:
        stop_event.wait(timeout=_RECORD_SECONDS)

    audio = np.concatenate(frames, axis=0) if frames else np.zeros((1, 1), dtype="float32")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, _SAMPLE_RATE)
    return tmp.name
