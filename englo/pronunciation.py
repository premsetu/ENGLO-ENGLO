"""Pronunciation scoring — two backends, auto-selected.

Local  (always available): Whisper word-probabilities + sequence alignment.
       Gives accuracy, completeness, fluency. Weak-phoneme detection uses a
       Hindi-speaker error map (no extra system deps).

Azure  (optional, superior): Azure Cognitive Services Pronunciation Assessment.
       Per-phoneme AccuracyScore + prosody. Enabled when AZURE_SPEECH_KEY and
       AZURE_SPEECH_REGION are set in the environment.
"""

from __future__ import annotations

import difflib
import os
import re
from typing import TYPE_CHECKING

from .models import PronunciationScore, STTResult

if TYPE_CHECKING:
    pass

# ── Phoneme hints for Hindi speakers ─────────────────────────────────────────
# Maps English word substrings → common error label shown to the tutor LLM.
_HINDI_PHONEME_TRAPS: list[tuple[str, str]] = [
    (r"\bth\b|^th|th$", "θ/ð (th-sound)"),
    (r"wh|^w",          "w (not v)"),
    (r"[aeiou]{2}",     "vowel cluster"),
    (r"tion$|sion$",    "ʃ (sh in -tion)"),
    (r"[^aeiou]r[^aeiou]", "r (retroflex risk)"),
    (r"^v",             "v (not b/w)"),
    (r"ed$",            "past-tense -ed ending"),
]


def _detect_weak_phonemes(word: str, prob: float) -> list[str]:
    """Return phoneme labels likely to be mispronounced given the word + confidence."""
    if prob >= 0.85:
        return []
    found = []
    lower = word.lower()
    for pattern, label in _HINDI_PHONEME_TRAPS:
        if re.search(pattern, lower) and label not in found:
            found.append(label)
    return found


def _normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words."""
    return re.sub(r"[^\w\s]", "", text.lower()).split()


# ── Local backend ─────────────────────────────────────────────────────────────

def score_local(stt_result: STTResult, target_text: str) -> PronunciationScore:
    """Score using Whisper word probabilities + sequence alignment."""
    target_words = _normalise(target_text)
    said_words = _normalise(stt_result.transcript)

    # Build word → probability map from STT (last occurrence wins for dupes)
    word_prob: dict[str, float] = {}
    for w in stt_result.words:
        word_prob[w.word.lower().strip(".,!?")] = w.probability

    # Sequence match: which target words were produced?
    matcher = difflib.SequenceMatcher(None, target_words, said_words, autojunk=False)
    matched_target: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("equal", "replace"):
            matched_target.extend(target_words[i1:i2])

    completeness = len(matched_target) / max(len(target_words), 1)

    # Accuracy = mean probability of all said words (proxy for how clearly spoken)
    probs = [w.probability for w in stt_result.words] if stt_result.words else []
    accuracy = sum(probs) / len(probs) if probs else 0.0

    # Fluency = fraction of words with probability ≥ 0.70 (fluent threshold)
    fluent_count = sum(1 for p in probs if p >= 0.70)
    fluency = fluent_count / len(probs) if probs else 0.0

    overall = 0.5 * accuracy + 0.3 * completeness + 0.2 * fluency

    # Weak-phoneme detection on low-confidence words
    weak: list[str] = []
    for w in stt_result.words:
        for label in _detect_weak_phonemes(w.word, w.probability):
            if label not in weak:
                weak.append(label)

    return PronunciationScore(
        overall=round(overall, 3),
        accuracy=round(accuracy, 3),
        completeness=round(completeness, 3),
        fluency=round(fluency, 3),
        weak_phonemes=weak,
        backend="local",
    )


# ── Azure backend ─────────────────────────────────────────────────────────────

def _azure_available() -> bool:
    return bool(os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION"))


def score_azure(audio_path: str, target_text: str) -> PronunciationScore:
    """Score via Azure Cognitive Services Pronunciation Assessment (per-phoneme)."""
    import azure.cognitiveservices.speech as speechsdk  # optional dep

    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
    )
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=target_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )
    pron_config.apply_to(recognizer)

    result = recognizer.recognize_once()
    pron_result = speechsdk.PronunciationAssessmentResult(result)

    # Collect weak phonemes (AccuracyScore < 60)
    weak: list[str] = []
    for word in (pron_result.words or []):
        for phoneme in (word.phonemes or []):
            if phoneme.accuracy_score < 60 and phoneme.phoneme not in weak:
                weak.append(phoneme.phoneme)

    overall = pron_result.pronunciation_score / 100.0

    return PronunciationScore(
        overall=round(overall, 3),
        accuracy=round(pron_result.accuracy_score / 100.0, 3),
        completeness=round(pron_result.completeness_score / 100.0, 3),
        fluency=round(pron_result.fluency_score / 100.0, 3),
        weak_phonemes=weak,
        backend="azure",
    )


# ── Public entry point ────────────────────────────────────────────────────────

def score(
    stt_result: STTResult,
    target_text: str,
    audio_path: str | None = None,
) -> PronunciationScore:
    """Auto-select Azure if credentials present, otherwise local."""
    if _azure_available() and audio_path:
        try:
            return score_azure(audio_path, target_text)
        except Exception:
            pass  # fall through to local on any Azure error
    return score_local(stt_result, target_text)
