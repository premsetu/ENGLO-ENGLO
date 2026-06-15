from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher

import anthropic

from . import mastery
from .bilingual import hindi_support_directive
from .models import Activity, ActivityType, LLMResponse, PronunciationScore, Verdict

_client: anthropic.Anthropic | None = None
_MODEL = os.getenv("TUTOR_LLM_MODEL", "claude-haiku-4-5-20251001")

# Force the offline heuristic grader regardless of key (handy for tests/demos)
_FORCE_LOCAL = os.getenv("TUTOR_LLM_LOCAL", "").lower() in {"1", "true", "yes"}

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
    """Grade a turn.

    Uses Claude when ANTHROPIC_API_KEY is set; otherwise falls back to a local
    heuristic grader so the loop runs fully offline (no key, no network).
    """
    if _FORCE_LOCAL or not os.getenv("ANTHROPIC_API_KEY"):
        return _local_evaluate(activity, transcript, pronunciation)
    try:
        return _claude_evaluate(activity, transcript, pronunciation)
    except (anthropic.APIError, anthropic.APIConnectionError):
        # Network/auth hiccup — degrade gracefully rather than break the turn.
        return _local_evaluate(activity, transcript, pronunciation)


# ── Offline heuristic grader ───────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _local_evaluate(
    activity: Activity,
    transcript: str,
    pronunciation: PronunciationScore,
) -> LLMResponse:
    """Key-free grader: blend lexical match with the pronunciation score.

    Verdict logic:
      - pass    : words match the target AND pron clears the success threshold
      - partial : words mostly match but pron is weak (or vice-versa)
      - fail    : little lexical overlap
    Feedback (correction + next line) is scaffolded by hindi_support.
    """
    target = _normalize(activity.target_text)
    said = _normalize(transcript)
    lexical = SequenceMatcher(None, target, said).ratio() if target else 1.0

    # Non-scored types (roleplay / conversation) are judged on lexical overlap only.
    pron_ok = True
    threshold = mastery.parse_pron_threshold(activity.success_criteria)
    if activity.type in {ActivityType.LISTEN_REPEAT, ActivityType.RECALL_DRILL}:
        pron_ok = pronunciation.overall >= threshold

    if lexical >= 0.80 and pron_ok:
        verdict = Verdict.PASS
    elif lexical >= 0.55:
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.FAIL

    correction, next_line, mix = _local_feedback(
        verdict, activity, pronunciation, said
    )
    return LLMResponse(
        verdict=verdict,
        correction=correction,
        next_spoken_line=next_line,
        language_mix=mix,
        notes_for_tracker={"grader": "local", "lexical": round(lexical, 2)},
    )


def _local_feedback(verdict, activity, pron, said):
    """Build a short spoken line + correction, scaffolded by hindi_support."""
    hs = activity.hindi_support
    target = activity.target_text

    if verdict is Verdict.PASS:
        if hs >= 0.7:
            return "", f"बहुत बढ़िया! Say it once more: {target}", "hi+en"
        if hs >= 0.4:
            return "", f"Very good! Next one.", "en"
        return "", "Perfect. Let's continue.", "en"

    if verdict is Verdict.PARTIAL:
        phon = pron.weak_phonemes[0] if pron.weak_phonemes else None
        tip = f" Focus on the {phon} sound." if phon else ""
        if hs >= 0.7:
            return (f"थोड़ा सा aur clear bolना hai.{tip}",
                    f"Almost! फिर से कहिए: {target}", "hi+en")
        if hs >= 0.4:
            return (f"Close!{tip}", f"Try again: {target}", "en")
        return (f"Almost there.{tip}", f"Once more: {target}", "en")

    # FAIL
    if hs >= 0.7:
        return ("कोई बात नहीं, फिर से सुनिए।",
                f"सुनिए और दोहराइए: {target}", "hi+en")
    if hs >= 0.4:
        return ("No problem, listen again.", f"Repeat after me: {target}", "en")
    return ("Let's try again.", f"Listen and repeat: {target}", "en")


# ── Claude grader ───────────────────────────────────────────────────────────────

def _claude_evaluate(
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
