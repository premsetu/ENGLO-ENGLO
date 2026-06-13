"""Bilingual scaffolding utilities.

Two responsibilities:
  1. Text segmentation — split a code-switched line into (text, lang) pairs so
     TTS can route each segment to the right voice.
  2. LLM directive generation — produce a concrete Hindi/English ratio instruction
     for the tutor system prompt, derived from the numeric hindi_support value.
"""

from __future__ import annotations

import re

# Devanagari Unicode block + Devanagari numerals, with optional trailing punctuation
# so that "शाबाश!" is captured as one Hindi token rather than "शाबाश" + "!".
_DEVANAGARI = re.compile(r"[ऀ-ॿ०-९][ऀ-ॿ०-९\s]*[!\.,;:?।\s]*")


_PUNCT_ONLY = re.compile(r"^[\s\.,!?;:\"'—\-]+$")


def split_segments(text: str) -> list[tuple[str, str]]:
    """Split a mixed Hindi/English string into (segment_text, 'hi'|'en') pairs.

    Punctuation-only fragments are merged into the preceding segment so that
    "शाबाश!" stays one Hindi segment rather than splitting into ("शाबाश","hi")
    + ("!","en").

    Example:
        "शाबाश! Your 'three' needs work." →
        [("शाबाश!", "hi"), ("Your 'three' needs work.", "en")]
    """
    raw: list[tuple[str, str]] = []
    last = 0

    for match in _DEVANAGARI.finditer(text):
        before = text[last : match.start()].strip()
        if before:
            raw.append((before, "en"))
        hindi_seg = match.group().strip()
        if hindi_seg:
            raw.append((hindi_seg, "hi"))
        last = match.end()

    tail = text[last:].strip()
    if tail:
        raw.append((tail, "en"))

    if not raw:
        return [(text, "en")]

    # Merge punctuation-only segments into their predecessor
    merged: list[tuple[str, str]] = []
    for seg_text, lang in raw:
        if merged and _PUNCT_ONLY.match(seg_text):
            prev_text, prev_lang = merged[-1]
            merged[-1] = (prev_text + seg_text, prev_lang)
        else:
            merged.append((seg_text, lang))

    return merged


def hindi_support_directive(ratio: float) -> str:
    """Return a concrete LLM instruction for the given hindi_support ratio.

    The ratio mirrors the level table in the spec:
      ~0.80 → L0 Bootstrap   (mostly Hindi)
      ~0.50 → L1 First sentences
      ~0.20 → L2 Everyday
      ~0.05 → L3 Confident
      0.00  → L4 Fluency     (English only)
    """
    if ratio >= 0.70:
        return (
            "Use Hindi for ALL meta-speech: instructions, corrections, encouragement, "
            "and explanations. Keep ONLY the target English phrase itself in English. "
            "Your next_spoken_line should be mostly Hindi with the English target embedded."
        )
    if ratio >= 0.40:
        return (
            "Mix Hindi and English roughly 50/50. Give corrections and new-concept "
            "explanations in Hindi; use English for encouragement and simple instructions. "
            "Set language_mix to 'hi+en'."
        )
    if ratio >= 0.10:
        return (
            "Speak mostly in English. Reserve Hindi only for important corrections when "
            "the learner is clearly confused — one Hindi sentence at most. "
            "Set language_mix to 'hi+en' if you use any Hindi, otherwise 'en'."
        )
    if ratio > 0.0:
        return (
            "Speak almost entirely in English. A single Hindi word of encouragement "
            "(e.g. शाबाश) is acceptable but not required. "
            "Set language_mix to 'en'."
        )
    return (
        "English only. Do not use any Hindi. Set language_mix to 'en'."
    )
