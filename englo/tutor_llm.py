from __future__ import annotations

import json
import os

import anthropic

from .bilingual import hindi_support_directive
from .models import Activity, LLMResponse, PronunciationScore, Verdict

_client: anthropic.Anthropic | None = None
_MODEL = os.getenv("TUTOR_LLM_MODEL", "claude-haiku-4-5-20251001")

_SYSTEM_PROMPT_BASE = """\
You are an expert English tutor for Hindi-speaking absolute beginners.
Your role is strictly as an EVALUATOR and RESPONDER for a single activity turn.
You do NOT decide what comes next — the course engine does that.

Fixed rules (never violate):
1. Correct only ONE point at a time — never overwhelm the learner.
2. Stay within the simplicity_level vocabulary — never introduce harder words.
3. Tone: warm, patient, encouraging. Beginners need confidence.
4. Keep `next_spoken_line` short and natural — it will be spoken aloud.
5. `language_mix` must be exactly one of: "hi", "en", "hi+en".
6. Respond ONLY with valid JSON matching the schema — no other text.

Hindi/English balance rule for THIS session:
{hindi_directive}
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def evaluate(
    activity: Activity,
    transcript: str,
    pronunciation: PronunciationScore,
) -> LLMResponse:
    # Build a ratio-specific system prompt so the LLM gets a concrete instruction,
    # not just a number it has to interpret itself.
    system_prompt = _SYSTEM_PROMPT_BASE.format(
        hindi_directive=hindi_support_directive(activity.hindi_support)
    )

    payload = {
        "activity": {
            "type": activity.type,
            "target_text": activity.target_text,
            "expected_pattern": activity.expected_pattern,
            "success_criteria": activity.success_criteria,
        },
        "learner_utterance_transcript": transcript,
        "pronunciation": {
            "overall": pronunciation.overall,
            "weak_phonemes": pronunciation.weak_phonemes,
        },
        "hindi_support": activity.hindi_support,
        "simplicity_level": activity.simplicity_level,
    }

    user_msg = (
        "Evaluate this learner turn. Return ONLY a JSON object with keys: "
        "verdict, correction, next_spoken_line, language_mix, notes_for_tracker.\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    client = _get_client()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        temperature=0.2,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)

    return LLMResponse(
        verdict=Verdict(data["verdict"]),
        correction=data.get("correction", ""),
        next_spoken_line=data["next_spoken_line"],
        language_mix=data.get("language_mix", "en"),
        notes_for_tracker=data.get("notes_for_tracker", {}),
    )
